import sqlite3
from .stats import Stat

sql = None  # pylint: disable=invalid-name


class OurDb(sqlite3.Connection):
    tracked_stats = None
    # pylint: disable=no-member

    def __init__(self, options):
        global sql  # pylint: disable=global-statement,invalid-name
        sql = self  # pylint: disable=invalid-name

        dbname = None
        if options and options.save:
            if options.module:
                dbname = options.module
            else:
                dbname = "anaphora"

            if options.save == "archive":
                import time

                dbname += "-" + time.ctime()

            dbname += ".db"

            if options.save == "replace":
                try:
                    import os

                    os.remove(dbname)
                except FileNotFoundError:
                    pass
            elif options.save == "track":
                # LATERDO something cute to create a schema for tracking runs
                reason = "longitudinal tracking in a single database isn't implemented yet; the 'archive' option can be used to save multiple datestamped databases (which you can merge on your own if necessary)."
                raise NotImplementedError(reason)
        else:
            dbname = ":memory:"

        super().__init__(
            dbname, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )

        self.row_factory = sqlite3.Row

        self.execute("PRAGMA foreign_keys=ON;")
        self.execute(
            """CREATE TABLE nouns(
                id INTEGER NOT NULL PRIMARY KEY,
                name TEXT
            );
        """
        )
        self.execute(
            """CREATE TABLE exceptions(
                id INTEGER NOT NULL PRIMARY KEY,
                e_class TEXT,
                e_context TEXT,
                e_message TEXT,
                e_traceback TEXT,
                e_output TEXT,
                e_line INTEGER,
                e_path TEXT,
                e_terminal INTEGER,
                node_id INTEGER REFERENCES nodes(id),
                ignore INTEGER
            );
        """
        )

    def add_exception(self, node, exception):
        self.execute(
            "INSERT INTO exceptions (e_class, e_message, e_traceback, e_output, e_line, e_path, e_context, e_terminal, node_id, ignore) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (
                exception.__class__.__name__,
                exception.message,
                exception.traceback.strip(),
                exception.output,
                exception.line,
                exception.path,
                exception.context,
                exception.terminal,
                node.id,
                node.ignored,
            ),
        )

    def setup_stat_table(self, stats):
        # the comma in here is wrong if there are no tracked stats; either we need default tracking or that needs to be magicked
        # nodes table
        self.execute(
            """CREATE TABLE IF NOT EXISTS nodes(
                id INTEGER NOT NULL PRIMARY KEY,
                description TEXT,
                parent_id INTEGER REFERENCES nodes(id),
                noun_id INTEGER REFERENCES nouns(id),
                {}
            );
        """.format(
                ", ".join([stat.create_sql for stat in stats])
            )
        )
        # aggregate table (mostly for joining on); this index is only valid for the child-most objects; it probably needs to be added to the existing aggregate!
        # I think that caveat (it's only valid for the child-most objects!) is my problem
        self.execute(
            """CREATE VIEW IF NOT EXISTS aggregate
                AS SELECT parent_id,
                {}
                FROM nodes
                GROUP BY parent_id;
        """.format(
                ", ".join([stat.sum_sql for stat in stats])
            )
        )

    def track_stats(self, stats):
        self.tracked_stats = stats
        self.setup_stat_table(stats)
        # LATERDO: not 100% sure we'll use this yet, but this means we use a single database file for test runs over time.
        # LATERDO: if they indicate they're saving this database when we're done, we'll create a metadata table for them containing information about the conditions under which the test was run and key specific test runs against it (versus a more naive version where we just save timestamped database files for each run)
        # self.execute(create meta)

    def clean_up(self, node):
        for stat in self.tracked_stats:
            stat.clean_up(node)

    def clear_stats(self):
        # self.tracked_stats = None
        # del self.tracked_stats
        Stat.rapture()
        self.close()  # pylint: disable=no-member

    def add_node(self, node):
        # this could fail, but we'll just let it raise for now
        cur = self.execute(
            "INSERT INTO nodes (description, parent_id, noun_id) VALUES (?, ?, ?);",
            (
                node.description,
                node.parent.id if node.parent else None,
                node.__class__.id,
            ),
        )
        return cur.lastrowid

    def update_node(self, node):
        self.execute(
            "WITH ag AS (SELECT * FROM aggregate WHERE parent_id={nodeid}) UPDATE nodes SET {query} WHERE nodes.id={nodeid};".format(
                query=", ".join((stat.update_sql for stat in self.tracked_stats)),
                nodeid=node.id,
            ),
            [stat.compute(node) for stat in self.tracked_stats],
        )

    def add_noun(self, noun):
        cur = self.execute("INSERT INTO nouns (name) VALUES (?);", (noun.__name__,))
        return cur.lastrowid


class QueryAPI(OurDb):

    """
    All queries return either an instance of sqlite.Row, or an iterator (sqlite.Cursor) which will return some number of these. You probably want to consume these one at a time by iterating on the cursor, but you may call `.fetchall()` or use `list` on the cursor to create a list of Row objects. On a row object, columns can be accessed either by list index (row[1]), or by column-name key (row["id"]). I recommend the latter. You can use dict(Row) for introspection purposes, but it's an unnecessary step for normal use.

    For queries which return nodes, the :id:, :depth:, :parent_id: and :noun_id: keys will always be present. Other included stats will depend on what stats the reporter's tracked_stats() function expressed interest in tracking. See documentation of Anaphora.Reporter class for how to declare interest.

    You are of course free to compose your own queries; this was one of the reasons for choosing an sql backend.
    """

    # pylint: disable=no-member

    # re-cycle common query parts
    query_templates = {
        "tree": """
            WITH RECURSIVE tree(id, depth) AS (
                SELECT id,
                        0 AS depth
                FROM nodes
                WHERE id={}
                UNION ALL
                SELECT child.id,
                        parent.depth + 1
                FROM nodes AS child
                JOIN tree AS parent ON child.parent_id=parent.id
                ORDER BY depth DESC, id ASC
            )
            {}
        """
    }
    # calculate the sql behind major queries and keep it here
    # both so we aren't calculating on call, and so other functions can use
    # the sql without forcing a call.
    # ideally also need some modular notions like, "with exceptions" and possibly "with noun" that can just be tacked onto the right queries.
    queries = {
        # not sure the exception part of this query is needed? or could be bolt-on?
        "tree": query_templates["tree"].format(
            1,
            """
            SELECT tree.depth, nodes.*, nouns.name, exceptions.e_class, exceptions.e_message, exceptions.e_traceback, exceptions.e_line, exceptions.e_path
            FROM tree
            JOIN nodes ON tree.id=nodes.id
            JOIN nouns ON nodes.noun_id=nouns.id
            LEFT OUTER JOIN exceptions ON exceptions.node_id=nodes.id
            """,
        ),
        "node_tree": query_templates["tree"].format(
            "?",
            """
            SELECT tree.depth, nodes.*
            FROM tree
            JOIN nodes ON tree.id=nodes.id
            """,
        ),
        "depths": query_templates["tree"].format(
            1,
            """
            SELECT DISTINCT depth, count(depth) as count
            FROM tree
            GROUP BY depth
            """,
        ),
        "depth": query_templates["tree"].format(
            1,
            """
            SELECT DISTINCT depth, count(depth) as count
            FROM tree
            WHERE depth=?
            GROUP BY depth
            """,
        ),
        "node_depths": query_templates["tree"].format(
            "?",
            """
            SELECT DISTINCT depth, count(depth) as count
            FROM tree
            GROUP BY depth
            """,
        ),
        "node_depth": query_templates["tree"].format(
            "?",
            """
            SELECT DISTINCT depth, count(depth) as count
            FROM tree
            WHERE depth=?
            GROUP BY depth
            """,
        ),
    }

    def tree(self, node_id=None):
        """
        Return iterator over nodes with depth information.

        Selects entire tree by default, or nodes below :node_id: otherwise.

        Each row will have a "depth" key which indicates its level in the tree structure.
        """
        return (
            self.execute(self.queries["node_tree"], (node_id,))
            if node_id
            else self.execute(self.queries["tree"])
        )

    def nodes(self):
        """
        Return iterator over nodes for entire run without depth information.
        """
        return self.execute("SELECT * FROM nodes ORDER BY id ASC;")

    def node(self, node_id):
        """
        Return node indicated by :node_id:.
        """
        return self.execute("SELECT * FROM nodes WHERE id=?;", (node_id,)).fetchone()

    def depths(self, node_id=None):
        """
        Return iterator over each distinct depth and the number of nodes at that depth.
        """
        return (
            self.execute(self.queries["node_depths"], (node_id,))
            if node_id
            else self.execute(self.queries["depths"])
        )

    def depth(self, node_id=None, depth=0):
        """
        Return the number of nodes that were found at a given :depth:.
        """
        return (
            self.execute(self.queries["node_depth"], (node_id, depth)).fetchone()
            if node_id
            else self.execute(self.queries["depth"], (depth,)).fetchone()
        )

    # def nouns(self):
    #   return

    # def noun(self, noun=None):
    #   return

    # ditto per exceptions
    def all_exceptions(self, count=False):
        return (
            self.execute("SELECT count(*) FROM exceptions;")
            if count
            else self.execute("SELECT * FROM exceptions;")
        )

    def ignored_exceptions(self, count=False):
        return (
            self.execute("SELECT count(*) FROM exceptions WHERE ignore == 1;")
            if count
            else self.execute("SELECT * FROM exceptions WHERE ignore == 1;")
        )

    def exceptions(self, count=False):
        return (
            self.execute("SELECT count(*) FROM exceptions WHERE ignore == 0;")
            if count
            else self.execute("SELECT * FROM exceptions WHERE ignore == 0;")
        )

    def warnings(self, count=False):
        return (
            self.execute("SELECT count(*) FROM exceptions WHERE ignore == 2;")
            if count
            else self.execute("SELECT * FROM exceptions WHERE ignore == 2;")
        )
