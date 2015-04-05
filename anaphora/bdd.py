import traceback, sys, inspect, datetime, sqlite3, resource, itertools, re, subprocess
from collections import defaultdict
#import coverage
from anaphora import meta, cover

class CONSTANTS(object):
	# runtime keys
	BEFORE = 0
	AFTER = 1
	DURING = 0

#exception mixins
class Benign(object):
	"""
	Benign exceptions are less serious than warnings.

	Example: assertion failure in a test.
	"""
	severity = "Benign exception"
	terminal = False

class Critical(object):
	"""
	Critical exceptions aren't quite fatal.

	The best distinction here is that these should probably be treated
	as fatal for developers testing what they're building, but a
	downstream user shouldn't be required to fix the exception before
	they can see what tests pass or fail.
	"""
	severity = "Critical error"

	#chicken and egg; config gets passed into the node and is a property of the node; one of the upsides of this model is that different nodes can get different configs, if for some reason that makes sense. The downside is that there's no obvious place for an object like this to go looking for the config to take actions on. In theory, the node will get passed in to the object and stored, though. So, let's try it.
	@property
	def terminal(self):
		if self.node.options and self.node.options.permissive:
			return False
		else:
			return True

#base exception types, not thrown
class AnaphoraException(Exception): pass

class TestRunException(AnaphoraException):
	template = "{severity} in {node} at line {line} of {loc}:"
	lineno = None
	filename = None
	node = None
	#severity = "default"
	initialized = False
	extra_exception = []

	def __init__(self, node, *args, **kwargs):
		self.node = node
		super().__init__()

	@property
	def exception(self):
	    return traceback.format_exception_only(self.__class__, self)

	@property
	def traceback(self):
	    return "\n".join(self.exception + self.extra_exception)

	def initialize(self):
		cause = self.__cause__ #this doesn't exist yet (it's added after init I guess)
		#We can start on line 1 if it's a body test, or line 3 otherwise
		if cause:
			stackfrom = 1 if isinstance(self, TestRunException) else 3

			#the error stack, from which we only want line 0, and 3+
			stack = traceback.format_exception(cause.__class__, cause, cause.__traceback__)
			tb = cause.__traceback__

			while tb:
				blame = tb
				tb = tb.tb_next
				# print("tb: %s" % blame)
				# print("lineno %s" % blame.tb_lineno)
				# print("filename %s" % blame.tb_frame.f_code.co_filename)

			# print("")
			# print("stack %s" % stack)
			# print("")
			#need the following; will any of these names clash?
			self.lineno = blame.tb_lineno
			self.filename = blame.tb_frame.f_code.co_filename
			self.extra_exception = [stack[0]]+stack[stackfrom:]
		else:
			self.lineno = self.__traceback__.tb_lineno
			self.filename = self.__traceback__.tb_frame.f_code.co_filename
		self.initalized = True

	def __str__(self):
		if not self.initialized:
			self.initialize()
		return self.template.format(severity=self.severity, line=self.lineno,
			loc=self.filename, node=self.node)


class HookError(TestRunException, Critical): pass

#thrown exceptions
class TestFailure(TestRunException, Benign):
	severity = "Assertion failed"
	loc = "test body"

class BeforeHookError(HookError):
	loc = "before hook"
class AfterHookError(HookError):
	loc = "after hook"
class TestError(TestRunException, Critical):
	loc = "test body"

class SkipNode(TestRunException, Benign):
	loc = "not sure this makes sense"

class OurDb(sqlite3.Connection):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.execute("PRAGMA foreign_keys=ON;")
		self.execute("""CREATE TABLE nouns(
				id INTEGER NOT NULL PRIMARY KEY,
				name TEXT
			);
		""")
		self.execute("""CREATE TABLE exceptions(
				id INTEGER NOT NULL PRIMARY KEY,
				e_class TEXT,
				e_message TEXT,
				e_traceback TEXT,
				e_line INTEGER,
				e_file TEXT,
				node_id INTEGER REFERENCES nodes(id),
				ignore INTEGER
			);
		""")

	#TODO: build some smart methods on the exceptions for handling most of this; these concepts have now been partially rehashed in three places now
	#Yes. This is essential.
	# def add_exception(self, node, exception):
	# 	try:
	# 		cause = exception[1].__cause__
	# 		#We can start on line 1 if it's a body test, or line 3 otherwise

	# 		stackfrom = 1 if isinstance(exception[1], TestFailure) else 3
	# 		#a brief description of the error
	# 		err = traceback.format_exception_only(exception[0], exception[1])

	# 		#the error stack, from which we only want line 0, and 3+
	# 		stack = traceback.format_exception(cause.__class__, cause, cause.__traceback__)
	# 		tb = cause.__traceback__

	# 		while tb:
	# 			blame = tb
	# 			tb = tb.tb_next
	# 		self.execute("INSERT INTO exceptions (e_class, e_message, e_traceback, e_line, e_file, node_id, ignore) VALUES (?, ?, ?, ?, ?, ?, ?);", (exception[0].__name__, str(exception[1]), "\n".join(err + [stack[0]]+stack[stackfrom:]), blame.tb_lineno, blame.tb_frame.f_code.co_filename, node.id, node.ignored))
	# 	except:
	# 		info = sys.exc_info()
	# 		traceback.print_exception(info[0], info[1], info[2])
	#
	def add_exception(self, node, exception):
		self.execute("INSERT INTO exceptions (e_class, e_message, e_traceback, e_line, e_file, node_id, ignore) VALUES (?, ?, ?, ?, ?, ?, ?);", (exception.__class__.__name__, str(exception), exception.traceback, exception.lineno, exception.filename, node.id, node.ignored))

	def setup_stat_table(self, stats):
		#the comma in here is wrong if there are no tracked stats; either we need default tracking or that needs to be magicked
		#nodes table
		self.execute("""CREATE TABLE IF NOT EXISTS nodes(
				id INTEGER NOT NULL PRIMARY KEY,
				description TEXT,
				parent_id INTEGER REFERENCES nodes(id),
				noun_id INTEGER REFERENCES nouns(id),
				{}
			);
		""".format(", ".join([stat.create_sql for stat in stats])))
		#aggregate table (mostly for joining on); this index is only valid for the child-most objects; it probably needs to be added to the existing aggregate!
		#I think that caveat (it's only valid for the child-most objects!) is my problem
		#either I have to make it valid, or I need more logic elsewhere to catch this
		#so when the stats update, child_blah is always == ag_blah where parent.id == this.id, which means either pulling a real rabbit out of the hat in that context, or figuring out SQL to make sure the view table is fucking correct? But the view can't really be. The point is just that
		self.execute("""CREATE VIEW IF NOT EXISTS aggregate
				AS SELECT parent_id,
				{}
				FROM nodes
				GROUP BY parent_id;
		""".format(", ".join([stat.sum_sql for stat in stats])))

	def track_stats(self, stats):
		self.tracked_stats = stats
		self.setup_stat_table(stats)
		# TODO: not 100% sure we'll use this yet, but this means we use a single database file for test runs over time.
		# if they indicate they're saving this database when we're done, we'll create a metadata table for them containing information about the conditions under which the test was run and key specific test runs against it (versus a more naive version where we just save timestamped database files for each run)
		# self.execute(create meta)
		...

	def clean_up(self, node):
		for stat in self.tracked_stats:
			stat.clean_up(node)

	def clear_stats(self):
		self.tracked_stats = None
		Stat.rapture() #dispose of statobs #TODO all sorts of entanglement to deal w/ here

	def add_node(self, node):
		#print(node.description)
		cur = None
		try:
			cur = self.execute("INSERT INTO nodes (description, parent_id, noun_id) VALUES (?, ?, ?);", (node.description, node.parent.id if node.parent else None, node.__class__.id))
			return cur.lastrowid
		except Exception as e:
			print("sql error in add_node: %s" % e)
			#print(e.args)

	def update_node(self, node):
		self.execute("WITH ag AS (SELECT * FROM aggregate WHERE parent_id={nodeid}) UPDATE nodes SET {query} WHERE nodes.id={nodeid};".format(query=", ".join((stat.update_sql for stat in self.tracked_stats)), nodeid=node.id), [stat.compute(node) for stat in self.tracked_stats])

	def add_noun(self, noun):
		cur = self.execute("INSERT INTO nouns (name) VALUES (?);", (noun.__name__,))
		return cur.lastrowid

	#TODO: rm print when I don't need debugz
	def execute(self, *args, **kwargs):
		# print(args)
		# print(kwargs)
		return super().execute(*args, **kwargs)

class QueryAPI(OurDb):
	"""
	All queries return either an instance of sqlite.Row, or an iterator (sqlite.Cursor) which will return some number of these. You probably want to consume these one at a time by iterating on the cursor, but you may call `.fetchall()` or use `list` on the cursor to create a list of Row objects. On a row object, columns can be accessed either by list index (row[1]), or by column-name key (row["id"]). I recommend the latter. You can use dict(Row) for introspection purposes, but it's an unnecessary step for normal use.

	For queries which return nodes, the :id:, :depth:, :parent_id: and :noun_id: keys will always be present. Other included stats will depend on what stats the reporter's tracked_stats() function expressed interest in tracking. See documentation of Anaphora.Reporter class for how to declare interest.

	You are of course free to compose your own queries; this was one of the reasons for choosing an sql backend.
	"""
	#re-cycle common query parts
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
	#calculate the sql behind major queries and keep it here
	#both so we aren't calculating on call, and so other functions can use
	#the sql without forcing a call.
	#ideally also need some modular notions like, "with exceptions" and possibly "with noun" that can just be tacked onto the right queries.
	queries = {
		"tree": query_templates["tree"].format(1, """
			SELECT tree.depth, nodes.*, nouns.name, exceptions.e_class, exceptions.e_message, exceptions.e_traceback, exceptions.e_line, exceptions.e_file
			FROM tree
			JOIN nodes ON tree.id=nodes.id
			JOIN nouns ON nodes.noun_id=nouns.id
			LEFT OUTER JOIN exceptions ON exceptions.node_id=nodes.id
			"""),
		"node_tree": query_templates["tree"].format("?", """
			SELECT tree.depth, nodes.*
			FROM tree
			JOIN nodes ON tree.id=nodes.id
			"""),
		"depths": query_templates["tree"].format(1, """
			SELECT DISTINCT depth, count(depth) as count
			FROM tree
			GROUP BY depth
			"""),
		"depth": query_templates["tree"].format(1, """
			SELECT DISTINCT depth, count(depth) as count
			FROM tree
			WHERE depth=?
			GROUP BY depth
			"""),
		"node_depths": query_templates["tree"].format("?", """
			SELECT DISTINCT depth, count(depth) as count
			FROM tree
			GROUP BY depth
			"""),
		"node_depth": query_templates["tree"].format("?", """
			SELECT DISTINCT depth, count(depth) as count
			FROM tree
			WHERE depth=?
			GROUP BY depth
			""")
	}

	#TODO: what do we still lack for traditional node-oriented queries?
	#aggregating pass/fail counts for a depth, or for node descendants, etc. query explicit v. implicit failures.

	def tree(self, node_id=None):
		"""
		Return iterator over nodes with depth information.

		Selects entire tree by default, or nodes below :node_id: otherwise.

		Each row will have a "depth" key which indicates its level in the tree structure.
		"""
		return self.execute(self.queries["node_tree"], (node_id,)) if node_id else self.execute(self.queries["tree"])

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
		return self.execute(self.queries["node_depths"], (node_id,)) if node_id else self.execute(self.queries["depths"])

	def depth(self, node_id=None, depth=0):
		"""
		Return the number of nodes that were found at a given :depth:.
		"""
		return self.execute(self.queries["node_depth"], (node_id, depth)).fetchone() if node_id else self.execute(self.queries["depth"], (depth,)).fetchone()

	#TODO: what kind of noun related stats might we want? a list of nouns, a list of nouns and the number of times they're used. a list of all nodes using a noun. A depth-list of each node using a noun and all of its descendants. A fail/succeed count for one or all nouns. A fail/succeed count for the trees below a noun.

	def nouns(self):
		return

	def noun(self, noun=None):
		return

	#ditto per exceptions
	def all_exceptions(self, count=False):
		return self.execute("SELECT count(*) FROM exceptions;") if count else self.execute("SELECT * FROM exceptions;")

	def ignored_exceptions(self, count=False):
		return self.execute("SELECT count(*) FROM exceptions WHERE ignore == 1;") if count else self.execute("SELECT * FROM exceptions WHERE ignore == 1;")

	def exceptions(self, count=False):
		return  self.execute("SELECT count(*) FROM exceptions WHERE ignore != 1;") if count else self.execute("SELECT * FROM exceptions WHERE ignore != 1;")



# Adapted from code by Oren Tirosh, MIT license per http://code.activestate.com/recipes/578231-probably-the-fastest-memoization-decorator-in-the-/
class CacheDict(dict):
	"""
	Memoize calls to a closure provided on init which accepts a single argument.
	"""
	def __init__(self, func):
		self.func = func
		super().__init__()

	def __missing__(self, key):
		ret = self[key] = self.func(key)
		return ret


class Stat(object):
	"""
	Represents a statistic which anaphora can track for each node.

	Here's a simple declaration for one of Anaphora's internal stats:
		Stat(lambda _: _.runtime["setup"]).called("setup").type("numeric")

	The Stat constructor's lone argument should be a closure which accepts a single argument. It will be called with the node object the stat is being computed for. Our convention is to name this argument _ for brevity and visual distinction. The stat object also expects to be given a string name via the `called` method and have a `type` declared. Valid types are in VALID_TYPES ({valid_types}), and the default is {column_type}.

	Core statistics are a little boring by themselves; the power and usefulness of the stat declaration system comes from composite statistics. Let's look at a pair:

		Stat(lambda _: _.stat("before") + _.stat("after")).called("hooks").type("numeric")
		Stat(lambda _: _.stat("hooks") + _.stat("setup") + _.stat("during") + _.stat("teardown")).called("runtime").type("numeric")

	The first statistic here, called _hooks_, is the sum of the core statistics tracked for time spent running the before and after hooks. You can see here that the node object has a convenience method, `stat`, which accepts the string name of a declared statistic and either computes the value and caches it, or pulls it directly from the cche.

	If you look carefully at the second statistic, called `runtime`, you'll notice that it's composed from the composite statistic `hooks`, and the core statistics `setup`, `during`, and `teardown`. Together, these are the full run time for a node. If the `hooks` value has already been calculated from the core `after` and `before` hook stats, it will just be pulled from the cache instead of being re-computed.

	The stats system will decompose every composite statistic as far as necessary to resolve it into a real value, caching each step along the way. While this isn't a huge deal for relatively simple stats, it can save a lot of time when it comes to tracking many composite sums, and computing many differences, percentages, percentage differences, etc. As such, it's usually best to compose each statistic from the smallest number of other statistics.

	It's also worth noting that only statistics in the tuple returned by a reporters `tracked_stats` method will be added to the database. You can take advantage of the caching to create untracked intermediary statistical units that are only used to compose other advanced units.
	"""
	VALID_TYPES = ("INTEGER", "NUMERIC", "REAL")
	column_type = VALID_TYPES[1]
	__doc__ = __doc__.format(valid_types=", ".join(map(str.lower, VALID_TYPES)), column_type=column_type.lower())
	PROPERLY_INITIALIZED = 2
	all_stats_go_to_heaven = {} #class global
	# using "format" style for consistency/clarity, but will actually
	# use .replace on these. This isn't a mistake; format just requires
	# more work to use without all kwargs present.
	how_to_create_me = "{name} {type} DEFAULT 0, child_{name} {type} DEFAULT 0"
	#ideally this would just be child_{name}=ag.{name} but sqlite doesn't seem to support this syntax. Possible TODO if there's an sqlite language update in future versions.
	how_to_update_me = "{name}=?, child_{name}=(SELECT ag_{name} FROM ag)"
	aggregator = "all"
	how_to_aggregate = {"all": "total(child_{name})+total({name}) as ag_{name}", "children":"(CASE WHEN sum(child_{name}) IS NULL THEN total({name}) ELSE total(child_{name}) END) as ag_{name}"}

	@property
	def how_to_aggregate_me(self):
	    return self.how_to_aggregate[self.aggregator]

	    #I think: aggregate all when the definition of a unit means they exclude each other
	def aggregate_all(self):
		self.aggregator = "all"
		return self

		#I think: aggregate_children when the definition means they include each other
		#i.e. my during time includes my child's during time, but it also includes a bunch of junk, the sum of my "during" time is the time spent in my children
	def aggregate_children(self):
		self.aggregator = "children"
		return self

	@property
	def initialized(self):
		return len(self.__initialized) == self.PROPERLY_INITIALIZED

	def __init__(self, closure):
		self.__initialized = set()
		self.__cache = CacheDict(closure) #node:value

	@classmethod
	def stat(cls, name):
		return cls.all_stats_go_to_heaven[name]

	@classmethod
	def rapture(cls):
		cls.all_stats_go_to_heaven = {}

	def called(self, name):
		self.name = name
		self.all_stats_go_to_heaven[name] = self
		# see defs in class head for note on .replace
		self.how_to_create_me = self.how_to_create_me.replace('{name}', name)
		self.how_to_update_me = self.how_to_update_me.replace('{name}', name)
		self.how_to_aggregate = {k:v.replace('{name}', name) for k,v in self.how_to_aggregate.items()}
		self.__initialized.add("called")
		return self

	def type(self, column_type):
		column_type = column_type.upper()
		if column_type in self.VALID_TYPES:
			self.column_type = column_type
			self.how_to_create_me = self.how_to_create_me.replace('{type}', column_type)
			self.how_to_aggregate = {k:v.replace('{type}', column_type) for k,v in self.how_to_aggregate.items()}
			self.__initialized.add("type")
		return self

	def compute(self, node):
		return self.__cache[node]

	@property
	def create_sql(self):
		if self.initialized:
			return self.how_to_create_me
		else:
			raise Exception("Attempting to create columns for a stat that wasn't properly initialized.")

	@property
	def update_sql(self):
		if self.initialized:
			return self.how_to_update_me
		else:
			# you'd have to be doing something willfully odd to get here; cut?
			raise Exception("Attempting to update columns for a stat that wasn't properly initialized.")

	@property
	def sum_sql(self):
		if self.initialized:
			return self.how_to_aggregate_me
		else:
			# you'd have to be doing something willfully odd to get here; cut?
			raise Exception("Attempting to create aggregate columns for a stat that wasn't properly initialized.")

	def clean_up(self, node):
		del self.__cache[node]


class RunnerMixin(object):
	"""
	Support functions for TestRunners.

	See the TestRunner class for details.
	"""
	before_ran = False

	def load(self, module_strs):
		self._modules = module_strs
		self.les_iterables = map(lambda x: Module(x), module_strs)
		self.before_run()
		return self

	def shell(self, shell_strs):
		self.les_iterables = map(lambda x: Shell(x), shell_strs)
		self.before_run()
		return self

	def __iter__(self):
		self.before_run()
		return self

	def __next__(self):
		try:
			return next(self.les_iterables)
		except StopIteration:
			self.after_run()
			raise

	def before_run(self):
		if self.before_ran:
			return
		if not self.id:
			self.__class__.id = self.db.add_noun(self.__class__)
		self.id = self.db.add_node(self)
		self.add()

		self.start_coverage()
		self.run_hooks(self.BEFORE)
		self.before_ran = True

	def after_run(self):
		self.run_hooks(self.AFTER)
		self.end_coverage()
		#TODO: succeed if we haven't failed may not ideal
		if self.succeeded == None:
			self.succeed()
		self.db.update_node(self)
		self.clean_up()

	# def classes(self, predicate=None):
	# 	return itertools.chain(*[x.classes(predicate) for x in self])

	# def functions(self, predicate=None):
	# 	return itertools.chain(*[x.functions(predicate) for x in self])

	# def modules(self, predicate=None):
	# 	return itertools.chain(*[x.modules(predicate) for x in self])

	# def methods(self, predicate=None):
	# 	return itertools.chain(*[x.methods(predicate) for x in self])

	def classes(self, predicate=None):
		def classifier(node):
			node.before_run()
			iters = node.classes(predicate)
			node.after_run()
		self.les_iterables = itertools.chain(*map(lambda x: x.classes(predicate), self.les_iterables))
		return self

	def functions(self, predicate=None):
		self.les_iterables = itertools.chain(*map(lambda x: x.functions(predicate), self.les_iterables))
		return self

	def modules(self, predicate=None):
		self.les_iterables = itertools.chain(*map(lambda x: x.modules(predicate), self.les_iterables))
		return self

	def methods(self, predicate=None):
		self.les_iterables = itertools.chain(*map(lambda x: x.methods(predicate), self.les_iterables))
		return self


class Noun(CONSTANTS, RunnerMixin):
	description = None
	environment_vars = None
	environment_var_keys = None
	hooks = None
	parent = None
	nouns = None
	coverage = None
	hook_error = None
	hook_error_type = None
	options = meta.config
	skip_me = False
	succeeded = None
	ignored = 0
	#LATERDO: after initial. some method to specify file in case user wants to keep db
	#db = QueryAPI(':memory:', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
	db = QueryAPI('temp.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
	db.row_factory = sqlite3.Row
	id = None # this gets assigned after we're inserted in the db.
	_current = [] #intentionally shared for class instances.

	def __init__(self, desc, *args, **kwargs):
		self._checkpoint = datetime.datetime.utcnow()
		self.parent = self.current
		self.description = desc
		self.exceptions = []
		self.nouns = []
		#LATERDO: will be interesting to figure out how to db this, perhaps it can wait
		#coverage stats disabled for now
		#self.coverage = {}
		self.reset_runtime()

		self.hooks = {self.BEFORE:[], self.AFTER:[]}
		if 'before' in kwargs:
			self.hooks[self.BEFORE].append(kwargs['before'])
		if 'after' in kwargs:
			self.hooks[self.AFTER].append(kwargs['after'])
		#TODO: this may be crazy. Basically the default is for options to go on the class, and if the class already has options to assume you meant to stick them on the node. This seems fragile. Probably needs better thinks.
		#Yes, this doesn't even work. We need to support a few models:
		#1. All nodes get their settings from the primary config object, of which a single copy exists. node.config = conf
		#2. By default, all nodes get their settings from the primary config object, but one class of nodes might get its config from some other shared location, node_class.config = conf
		#3. By default, all nodes get their settings from the primary config, but one class of nodes gets its config from a second shared location, and one specific node of this type has an explicitly-set config which differs from all of the above and is local to that instance. node_instance.config = conf
		#I can achieve 1 through the class variable declaration, but the dynamic grammar generation makes the second model to swing without having something explicit in the init routine or on the object for setting the config on the class or the instance.

	@property
	def current(self):
		if len(self._current):
			return self._current[-1]
		else:
			return None

	def add(self):
		#print("adding %s which has parent: %s" % (self, self.parent))
		self._current.append(self)

	def remove(self):
		self._current.pop()

	def grammar(self, names):
		for name in names:
			if isinstance(name, str):
				new_class = type(name, (Noun,), {})
				inspect.currentframe().f_back.f_locals[name] = new_class
				self.nouns.append(new_class)
			elif isinstance(name, Noun):
				self.nouns.append(name)

		return self

	def config(self, options):
		self.options = options

	def __enter__(self):
		#print("entering: %s" % self.description)
		if not self.id:
			self.__class__.id = self.db.add_noun(self.__class__)

		self.id = self.db.add_node(self)
		self.environment_vars = inspect.currentframe().f_back.f_locals

		#a "magic" var tentatively named _ is available with some special methods for controlling tests in ways we can't otherwise? Meh. Make them manually name it to access this.
		#self.environment_vars['_'] = self
		self.environment_var_keys = set(self.environment_vars.keys())
		self.add()

		#TODO: turn coverage back on?
		#self.cov = coverage.coverage(branch=True, omit="*anaphora/__init__.py")#, , omit=["test.py", "*colorama*"]plugins=["plugin"]
		# in the cli model this is parsed out of the command options...
		# print(__file__)
		self.start_coverage()
		#self.cov = coverage.coverage(branch=True)
		#self.cov = coverage.coverage(branch=True, omit=[__file__, "*anaphora/__init__.py"])
		#self.cov = coverage.coverage(branch=True, omit=["*%s.py" % self.options.file, "*anaphora/__init__.py"])
		#self.cov.start()

		# we are now on the *user's* time, be fleet of foot
		self.run_hooks(self.BEFORE)
		#print("about to run: %s" % self.description)
		self.entered = True
		return self

		#TODO: decompose this so it's a little more self-documenting?
	def __exit__(self, exception_type, exception_value, tb):
		skip = False
		#print("exiting: %s" % self.description)

		if exception_type is not None:
			#print("exception_type: %s" % exception_type)
			if isinstance(exception_value, SkipNode):
				#print("caught skip for: %s" % self.description)
				exception_type, exception_value, tb = (None,None,None)
				skip = True
			elif exception_type == SystemExit:
				sys.exit(exception_value)
			elif isinstance(exception_value, TestError):
				if exception_value.terminal:
					return False
			elif isinstance(exception_value, AssertionError):
				#chain an error off the actual exception to add value
				try:
					raise TestFailure(self) from exception_value
				except TestFailure as e:
					self.exception(e)
					exception_value = e

		# there was an error in a before hook, so we'll create a hook error based on it
		# and add it to the list of exceptions for this node
		if self.hook_error_type == self.BEFORE:
			self.end_coverage()
			try:
				raise BeforeHookError(self) from self.hook_error
			except BeforeHookError as e:
				self.exception(e)
				exception_type = BeforeHookError
				exception_value = e
				if e.terminal:
					raise

		self.run_hooks(self.AFTER)

		if self.hook_error_type == self.AFTER:
			self.end_coverage()
			try:
				raise AfterHookError(self) from self.hook_error
			except AfterHookError as e:
				self.exception(e)
				exception_type = AfterHookError
				exception_value = e
				if e.terminal:
					raise

		if skip:
			pass
		elif exception_type is not None:
			self.fail()
			if not isinstance(exception_value, TestRunException):
				#chain an error off the actual exception to add value
				try:
					raise TestError(self) from exception_value
				except TestError as e:
					self.exception(e)
					exception_value = e
					if e.terminal:
						raise
		else:
			self.succeed()

		#scrub namespace
		for x in (self.environment_vars.keys() - self.environment_var_keys):
			del self.environment_vars[x]

		self.db.update_node(self)
		self.clean_up()
		return True

	def start_coverage(self):
		return
		self.cov = coverage.coverage(branch=True)
		self.cov.start()

	def end_coverage(self):
		return
		self.cov.stop()
		self.cov.save()
		reporter = cover.Dict(self.cov, self.cov.config)
		self.coverage = reporter.statistics(None)

	def stat(self, name):
		return Stat.stat(name).compute(self)

	def reset_runtime(self):
		self.runtime = datetime.timedelta()

	def clean_up(self):
		#TODO: knowledge-sink for tasks we have to perform to remove references to this node. Ideally we'll do this through putting a function on all of the objects that need to forget us which accepts a node object and scrubs references to it.
		#likely suspects: OurDb
		#individual stat caches
		self.db.clean_up(self)
		self.remove()

	@classmethod
	def turn_out_the_lights(cls):
		cls.db.clear_stats()
		cls.db = None

	def checkpoint(self):
		temp = self.runtime = datetime.datetime.utcnow() - self._checkpoint
		self._checkpoint = datetime.datetime.utcnow()
		return temp

	# the db converts True/False and returns 1/0 on query
	# so going to stick to what the db wants instead of forcing a
	# conversion going in and another coming out
	# a skipped node will have a value of None, which the db api will preserve
	def succeed(self):
		self.succeeded = 1

	#stats
	def fail(self):
		self.succeeded = 0

	def exception(self, exception):
		self.exceptions.append(exception)
		self.db.add_exception(self, exception)

	def __str__(self):
		return "%s: %s" % (self.__class__.__name__, self.description)

	def run_hooks(self, kind):
		try:
			for hook in self.hooks[kind]:
				hook(self)
		except Exception as e:
			# can't raise here or it'll terminate with statement and pass
			# error up to parent's __exit__; we still need the error, so
			# save for use in our own exit func later.
			self.hook_error_type = kind
			self.hook_error = e

	def report(self):
		if self.reporter:
			return self.reporter.report(self)
		else:
			return 'nein reportage'

	## "special" functions for controlling some specific tests
	def skip(self):
		"""Skip execution of a node."""
		self.reset_runtime()
		# TODO: Are there any other clean-up tasks we need?
		raise SkipNode(self)

	# parts of our own test suite must be able to "fail" to properly test parts
	# of Anaphora that deal with test failures. In order to pass our own test
	# suite, we have to be able to ignore these failures.
	def ignore(self):
		"""
		Node is executed and failure tracked, but node is marked as ignored.

		When using default reporters, failures on ignored nodes don't influence
		the run's exit status. This is intended to let us collect information
		from tests that aren't critical (for example, a linter that may require
		significant work to comply with).

		It's worth noting that custom reporters have complete control over whether
		they report ignored nodes or allow them to influence the run status.
		"""
		self.ignored = 1


def convert(converter):
	"""Wrap module/class/func/method objects with a special node object."""
	def matching(f):
		def match(self, predicate=None):
			if predicate:
				self.les_iterables = (converter(ob) for key, ob in f(self) if predicate(key))
			else:
				self.les_iterables = (converter(ob) for key, ob in f(self))
			return self
		return match
	return matching

#TODO: I may be lacking two sorts of god-mode here:
	# a folder selector for running all python modules in a directory? Can python's default behavior with blank __init__.py just be leveraged here?
	# an executable runner

class TestRunner(Noun):
	"""
	Scaffold for running other types of test within an Anaphora run.

	Broadly, this enables a few uses of Anaphora:
	1. Folding tests written before Anaphora was in use into Anaphora's structured approach.
	2. Architecting an Anaphora run that spans many types of test.
	"""
	runnable = False
	def __init__(self, ob, *args, **kwargs):
		self.ob = ob
		name = ""
		if hasattr(ob, "__module__"):
			name += ob.__module__ + "."
		if hasattr(ob, "__self__"):
			name += ob.__self__.__class__.__name__ + "."
		name += ob.__name__
		super().__init__(name, *args, **kwargs)

	def run(self, *args, **kwargs):
		self.before_run()
		ran = None

		try:
			ran = self.execute(*args, **kwargs)
			self.succeed()
		except (AssertionError, subprocess.CalledProcessError) as e:
			try:
				raise TestFailure(self) from e
			except TestFailure as e:
				self.exception(e)
				if e.terminal:
					raise
		except Exception as e:
		#TODO: this is hungry; it eats all errors and won't help us debug any coding errors in external tests
			try:
				raise TestError(self) from e
			except TestError as e:
				self.exception(e)
				if e.terminal:
					raise

		self.after_run()
		return ran

	def execute(self, *args, **kwargs):
		raise NotImplementedError


class Callable(TestRunner):
	runnable = True
	def execute(self, *args, **kwargs):
		return self.ob(*args, **kwargs)


class Function(Callable):
	...


class Method(Callable):
	...


class Class(TestRunner):
	@property
	def ob(self):
		return self._ob
	@ob.setter
	def ob(self, value):
		self._ob = value() #create an instance of the class? do we need to be able to call it? manually instantiate it ourselves? would that much control be overkill?

	@convert(Method)
	def methods(self):
		return inspect.getmembers(self.ob, inspect.ismethod)

#try to import the first time self.ob gets accessed and then yield the imported object
class Module(TestRunner):
	runnable = True
	def __init__(self, module_str, *args, **kwargs):
		self.delay_init = module_str
		self.lazy_constructor = self._construct()
		super(TestRunner, self).__init__("", *args, **kwargs)

	@property
	def ob(self):
		return next(self.lazy_constructor)
	@ob.setter
	def ob(self, value):
		self._ob = value

	def construct(self):
		temp = __import__(self.delay_init, {}, None, [1], 0)
		self.ob = temp
		self.description = temp.__name__
		del self.delay_init

	def _construct(self):
		self.construct()
		while True:
			yield self._ob

	def execute(self, *args, **kwargs):
		return self.construct()

	@convert(lambda x: Module(x))
	def modules(self):
		return inspect.getmembers(self.ob, inspect.ismodule)

	@convert(Class)
	def classes(self):
		return inspect.getmembers(self.ob, inspect.isclass)

	@convert(Function)
	def functions(self):
		return inspect.getmembers(self.ob, inspect.isfunction)


class Shell(TestRunner):
	runnable = True

	def __init__(self, ob, *args, **kwargs):
		name = self.ob = ob
		super(TestRunner, self).__init__(name, *args, **kwargs)

	def execute(self, *args, **kwargs):
		return subprocess.check_call(self.ob, shell=True)


Anaphora = Noun("AnaphoraSingleton")

def clean_up():
	Noun.turn_out_the_lights()
