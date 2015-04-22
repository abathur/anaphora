"""Support tracking user-defined composable statistics."""
from anaphora.utils import CacheDict


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
	FULLY_INITIALIZED = 2

	column_type = VALID_TYPES[1]
	__doc__ = __doc__.format(valid_types=", ".join(map(str.lower, VALID_TYPES)), column_type=column_type.lower())

	all_stats_go_to_heaven = {}  # class global

	aggregator = "all"

	@property
	def how_to_aggregate_me(self):
		return self.how_to["aggregate"][self.aggregator]

		# I think: aggregate all when the definition of a unit means they exclude each other
	def aggregate_all(self):
		self.aggregator = "all"
		return self

		# I think: aggregate_children when the definition means they include each other
		# i.e. my during time includes my child's during time, but it also includes a bunch of junk, the sum of my "during" time is the time spent in my children
	def aggregate_children(self):
		self.aggregator = "children"
		return self

	@property
	def initialized(self):
		return len(self.__initialized) == self.FULLY_INITIALIZED

	def __init__(self, closure):
		self.__initialized = set()
		self.__cache = CacheDict(closure)
		# using "format" style for consistency/clarity, but will actually
		# use .replace on these. This isn't a mistake; format just requires
		# more work to use without all kwargs present.
		self.how_to = {
			"create": "{name} {type} DEFAULT 0, child_{name} {type} DEFAULT 0",
			"update": "{name}=?, child_{name}=(SELECT ag_{name} FROM ag)",
			"aggregate": {
				"all": "total(child_{name})+total({name}) as ag_{name}",
				"children": "(CASE WHEN sum(child_{name}) IS NULL THEN total({name}) ELSE total(child_{name}) END) as ag_{name}"
			}
		}
		self.name = None

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
		self.how_to["create"] = self.how_to["create"].replace('{name}', name)
		self.how_to["update"] = self.how_to["update"].replace('{name}', name)
		self.how_to["aggregate"] = {key: value.replace('{name}', name) for key, value in self.how_to["aggregate"].items()}
		self.__initialized.add("called")
		return self

	def type(self, column_type):
		column_type = column_type.upper()
		if column_type in self.VALID_TYPES:
			self.column_type = column_type
			self.how_to["create"] = self.how_to["create"].replace('{type}', column_type)
			self.how_to["aggregate"] = {key: value.replace('{type}', column_type) for key, value in self.how_to["aggregate"].items()}
			self.__initialized.add("type")
		return self

	def compute(self, node):
		return self.__cache[node]

	@property
	def create_sql(self):
		if self.initialized:
			return self.how_to["create"]
		else:
			raise Exception("Attempting to create columns for a stat that wasn't properly initialized.")

	@property
	def update_sql(self):
		if self.initialized:
			return self.how_to["update"]
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
