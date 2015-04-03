import colorama, traceback
from .bdd import TestError
from types import MethodType
from .bdd import Stat

colorama.init(autoreset=True)

#TODO: say what? was this just for debug?
def noneprint(arg):
	if arg == None:
		traceback.print_stack()
	else:
		oldprint(arg)
oldprint = print
print = noneprint

# stub that will remove colorama color codes for plaintext reporters
class NoOp(object):
	def __getattr__(self, name):
		return ""

# base class for all reporters is uncolored
# TODO: Need a way to easily swap color modes and easily declare strings once.
class ColorLlama(NoOp):
	Fore = NoOp()
	Back = NoOp()
	Style = NoOp()

class Reporter(object):
	viz = ""
	"""
	Base reporter class. The only strict requirements for subclasses is that they
	must:
	1. implement a report function which accepts a single argument, a copy of the
	anaphora object being reported on.

	2. implement a register_format_strings function which accepts no argument. The user
	is free to do nothing with this function if they wish, but users are encouraged
	to build all static information into their format strings only once; this method
	is only recycled if
	To minimize time wasted time in the reporting process, format strings should be
	built as class or instance variables with all information that is knowable before
	reporting-time.
	"""
	#TODO a syntax for declaring what information on the nodes this reporter will
	#actually make use of, which the Noun class can use to skip tracking unused stats
	#priority 1 is efficiency/time savings, and 2 is the usefulness of the syntax

	def __init__(self, colorizer=colorama):
		try:
			self.register_format_strings(colorizer)
		except NotImplementedError:
			pass

	def color(self):
		global colorama
		self.register_format_strings(colorama)

	def uncolor(obj):
		global ColorLama
		self.register_format_strings(ColorLlama)

	def report(self, testrun):
		raise NotImplementedError

	def tracked_stats(self):
		"""Must return a tuple of stats this reporter wants tracked."""
		raise NotImplementedError

	def register_format_strings(self, fmt): #self, fmt
		raise NotImplementedError

	def format_nested_exceptions(self, node, indent=0):
		"""Return a string containing a nested-format list of all exceptions."""
		out = []
		pad = "\n{: >{pad}}{viz}".format("", pad=indent*2, viz="")
		#we are double-checking stats.failed and this should be optimizable
		if node.stats.failed:
			#we have to self-pad the first string; join won't
			out.append(pad+"__{:_<{left}}".format(str(node), left=76-indent*2))
			for exception in node.stats.exceptions:
				tb = self.format_our_exception(exception)
				for line in tb:
					out += [self.viz + x for x in line.splitlines()]
				out += [""]
		out += [self.format_nested_exceptions(child, indent+1) for child in node.children if child.stats.failed]
		return pad.join(out)

	def format_flat_exceptions(self, exceptions):
		"""Return a string containing a flat-format list of all exceptions."""
		return "\n".join([self.format_exception(exception) for exception in exceptions])

	def format_exception(self, exception):
		"""Return a string containing a single exception."""
		return "{:=^80}\n{:}".format(str(exception[1].node), "".join(self.format_test_exception(exception)))

	def format_our_exception(self, exception):
		"""
		Return a string containing a specially-formatted exception.

		The _special_ part is just to remove anaphora's code from the traces.
		"""
		cause = exception[1].__cause__
		#We can start on line 1 if it's a body test, or line 3 otherwise
		stackfrom = 1 if isinstance(exception[1], TestError) else 3

		#a brief description of the error
		err = traceback.format_exception_only(exception[0], exception[1])

		#the error stack, from which we only want line 0, and 3+
		stack = traceback.format_exception(cause.__class__, cause, cause.__traceback__)
		return err + [stack[0]]+stack[stackfrom:]

	def cumulative_times(self, node):
		if len(node.children):
			out = {"hook":0,"anaphora":0, "total":0}
			for child in node.children:
				for k,v in self.cumulative_times(child).items():
					out[k] += v
			return out
		else:
			return {"hook":node.stats.hook_overhead()*1000,"anaphora":node.stats.anaphora_overhead()*1000, "total":node.stats.run_time()*1000}

	def test_stats(self, node):
		"""
		I run into a problem here with reporting useful statistics to the user because of how these things get counted. The current counting method is to only count failures and successes for items without children. So if you aren't hyper regular with the structure of your test blocks, it's possible for several different block elements to get counted.
		The other way to probably do this is to count totals and also to aggregate per block type, so we know that 4 features, 3 needs 8 goals and 21 requirements failed. I could probably achieve both of these by updating the fail/succeed functions to use a dict?
		The consternation over what to count implies we should just let the user define what gets counted (or, more likely, what we bother reporting).
		Maybe a really advanced use case I'd like to eventually support can help guide me. Let's say I chunk tests under 6 features (ABCDEF) and I want to see my tests broken out by feature. But my tests aren't strictly structured by feature, they're structured by user role. So in a few cases where roles have different uses for a feature, the feature gets repeated in more than one role. What supports a run like that? At this point we're talking about some sort of query language, because we can't aggregate. An SQLITE :memory: db would be one approach.
		Another might be providing a reporting api that performs these queries over the objects (or, of course, still using sqlite + these queries.)
		What would database structure look like? Or is this a graph database?
		It seems like maybe I can use the class to track instances and query this way, as long as we don't start needing very fancy things. And this is where the sqlite version starts looking attractive.
		"""
		return "test statz"
		stats = node.stats.stats()
		out = ["Test results:"]

		columnar = "{:%d} {:9} {:8}" % max(map(len, stats[1].keys()))
		out.append(columnar.format("type", "successes", "failures"))

		for key in stats[1]:
			out.append(columnar.format(key, stats[1][key], stats[2][key]))

		print(stats)
		return "\n".join(out)
		#return "{stats[1]:d} {stats[2]:d}".format(stats=node.stats.stats())

	def runtime_summary(self, node):
		#print(dict(node))
		#a lot of these stats can be though of loosely as lies when looked at per node. For example, the "hooks" time of the top node only reflects time spent parsing *its* hooks, and not time spent processing hooks on any sub node. This isn't _wrong_ as much as it is prone to being unintuitive. Likewise, it's "during" time is a bit of a lie; it's claiming a "during" time for alllll of the sub nodes, including all of the overhead time spent parsing them. Again, this isn't entirely "wrong"; there's a case for it to be intuitive for the "during" segment to hold all sub-nodes.
		#It's possible that the problem is just poor terminology. There may be a terminology that makes it clear--in one case we're counting everything that happens in the whole program while this node is running, while in another we're just presenting cumulative execution time of terminal nodes.
		#There's a bigger question here of whether it's even possible to let users easily declare something like this latter cumulative type, or if we just have to write them in sql. In sql it seems quite doable. If we're aware they need some cumulative tracking it's also trivial to make them aggregate on their parent. It might also be the case that it makes no sense to try to track a stat like "tests" or even "succeeded" or "failed" in the aggregate because of the semantic issues they pose in our context. it might be best to just do retroactive per-noun stats. It's much more plausible to say that two apps passed at an average time of 150ms/app, or that 27 features passed at an average of 40ms/feature.
		#It may be worth noting that by the time a node ends, all of its children will have terminated (and their nodes cleaned up...), so any cumulative tracking would have to be passed up to the parent at cleanup time.
		#time_actually_spent_in_me
		#sum_of_all_sub_node_durations (i.e., excluding all setup time.)
		#time_actually_spent_in_my_hooks
		#sum_of_all_sub_node_hook_time
		#TODO: time per /X should only be calculated per node type (X/app, x/requirement, x/feature)
		return "Run time: {:,.4f}s".format(node["during"])

	def tracked_stats(self):
		"""
		Return a tuple of Stat objects that the reporter wants to use.

		anaphora has a core set of tracked statistics, and a flexible system
		for defining additional statistics as operations on other stats; anaphora
		will compute statistics your reporter declares and save them alongside each
		node in the database. This gives you some control over the tradeoffs between
		having more statistics available, and time spent computing them. Your control
		over what gets saved is absolute, but anaphora's core statistics still
		accrue internally whether you use them or not.

		Below is an example of a basic stat tuple. The first 5 are core statistics,
		but the last two are composite calculations on these.
		(
			Stat(lambda _: _.runtime[C.SETUP].total_seconds()).called("setup").type("numeric"),
			Stat(lambda _: _.runtime[C.BEFORE].total_seconds()).called("before").type("numeric"),
			Stat(lambda _: _.runtime[C.DURING].total_seconds()).called("during").type("numeric"),
			Stat(lambda _: _.runtime[C.AFTER].total_seconds()).called("after").type("numeric"),
			Stat(lambda _: _.runtime[C.TEARDOWN].total_seconds()).called("teardown").type("numeric"),
			#composite time stats
			Stat(lambda _: _.stat("before") + _.stat("after")).called("hooks").type("numeric"),
			Stat(lambda _: _.stat("hooks") + _.stat("setup") + _.stat("during") + _.stat("teardown")).called("runtime").type("numeric")
		)

		See the bdd.Stat class for a detailed discussion of how to compose stats and how they're computed.
		"""
		return ()


class Minimal(Reporter):
	def report(self, testrun):
		print("Completed {0} of {1} tests in {2:,.4f}ms".format(testrun.stats.successes, testrun.stats.successes+testrun.stats.failures, testrun.stats.run_time()*1000))
		print(self.format_flat_exceptions(testrun.stats.exceptions))

class Default(Reporter):

	def register_format_strings(self, fmt):
		#print(blargs)
		self.describe_str = "%s:" + " %-*s" #TODO
		self.summarized_parent_str = "["+fmt.Fore.GREEN + "{0:>{statlen}}" + fmt.Fore.RESET + "|" + fmt.Fore.RED + "{1:<{statlen}}" + fmt.Fore.RESET + "]" #TODO
		self.summarized_childless_str = "["+fmt.Fore.GREEN+"{0:>{statlen}}"+fmt.Fore.RESET+"|"+fmt.Fore.RED+"{1:<{statlen}}"+fmt.Fore.RESET+"]" #TODO

	def report(self, testrun):
		print(self.runtime_summary(testrun))
		self.detailed_node(testrun, 2)

	def runtime_detail(self, node):
		"""
		terms:
		test overhead = tover = before hooks, after hooks, setup, teardown or sum - during
		framework overhead = fover = setup, teardown or sum - before/after hooks and during

		There are a lot of ways to give any detail on runtime:
		- sum(runtimes); this includes time we waste and time you waste
		- sum(runtimes) (%overhead)
		- sum(runtimes) (overhead)
		- during + sum(before, after, setup, teardown (collectively "overhead"))
		- ...

		So perhaps it's better to think in terms of what this information would give me and the scenarios under which I want it. I want to know how long my tests take to run in total, and I want to know where there are slow tests. And when there are slow test trees, I want a sense of how much of the time spent there I am responsible for (i.e., what portion I can actually save myself, and what portion is hidden in the framework.)
		The hitch here is that the top node's 'during' time actually includes tons of lower-level overhead. The top node's 'during' is really the sum of all child-node durings.
		In a sense I could argue it makes no sense to continue tracking 'during' time once I enter a child node, yeah? It might just be easiest to assemble the stats I want with a walk at the end rather than trying to track them as we go.
		"""
		runtimes = node.stats.runtimes()
		return " ".join(["{:15,.4f}ms".format(x*1000) for x in runtimes+[sum(runtimes)]])

	"""
	I need support here for some notion of a reporter class which can pluggably reconfigure the reporting output substantively. I can go ahead and make this initial version "work" for testing purposes first, but the inevitable next step is pulling it out into a separate class which also serves as a model for how users of anaphora can customize their reports (an even neater trick might be interoperability with mocha reporters?)

	Let's go ahead and get this done early while separation is less painful.
	"""
	def describe(self, node, pad_to, wrap_at):
		import textwrap

		return textwrap.fill(self.describe_str % (node.__class__.__name__, wrap_at, node.description), width=wrap_at, subsequent_indent=" "*(pad_to+len(node.__class__.__name__)+2))

	def summarized_node(self, node):
		stats = node.stats.stats()
		if len(node.children):
			return self.summarized_parent_str.format(stats[node.stats.SUCCESSES] if stats[node.stats.SUCCESSES] > 0 else "", stats[node.stats.FAILURES] if stats[node.stats.FAILURES]	 > 0 else "", statlen=8)
		else:
			if node.stats.failures:
				return self.summarized_childless_str.format("", "FAIL", statlen=8)
			else:
				return self.summarized_childless_str.format("PASS", "", statlen=8)

	def detailed_node(self, node, level):
		print(self.runtime_detail(node))
		for child in node.children:
			if level > 0:
				print(self.detailed_node(child, level-1))
			elif level == 0:
				print(self.summarized_node(child))

class Tree(Reporter):
	def register_format_strings(self, fmt):
		base = "{: <{pad}}{:}: {:}"
		self.desc_str = [fmt.Fore.RED+base, base, fmt.Fore.YELLOW+base]
		self.viz = "  "+fmt.Back.RED+" "+fmt.Back.RESET+" "

	def report(self, run):

		# print("SQL REPORT TEST SEQUENCE")
		for exception in run.db.execute("SELECT * FROM exceptions;"):
			print(exception["e_traceback"])
			print(exception["e_file"])
			print(exception["e_line"])
		# print(run.db.execute("SELECT * FROM nouns;").fetchall())
		print([dict(x) for x in run.db.execute("SELECT * FROM nodes WHERE description LIKE '%test%';").fetchall()])
		# #print(run.db.execute("SELECT * FROM nodes JOIN nodes ON nodes.parent_id =  LIMIT 10;").fetchall())

		# for row in run.db.tree():
		# 	#print(dict(row))
		# 	#print(("    "*depth)+str(nid)+"::"+desc)
		# 	print(("    "*row["depth"])+str(row["id"])+"::"+row["description"])
		# for row in run.db.nodes():
		# 	print(row["id"])
		# 	#print(("    "*depth)+str(nid)+"::"+desc)
		# for row in run.db.tree(8):
		# 	#print(dict(row))
		# 	print(("    "*row["depth"])+str(row["id"])+"::"+row["description"])
		print(dict(run.db.depths()))
		#print(dict(run.db.execute("SELECT sum()")))
		# print(dict(run.db.depth(2)))
		# print(dict(run.db.node(2)))
		# print(dict(run.db.depths(node_id=2)))
		# print(run.db.depths(node_id=2).fetchall())
		# print(dict(run.db.execute("SELECT sum(failures) FROM nodes;").fetchone()))
		for index, node in enumerate(run.db.tree()):
			# 0 == whole run; just compile overall things here.
			if index == 0:
				runtime_summary = self.runtime_summary(node)
				test_stats = self.test_stats(node)
			if node["depth"] > 0:
				print(self.describe(node))
			if node["e_message"]:
				print("exception on this node")

		print(runtime_summary)
		print(test_stats)

		return
		#print("A total of {:} exceptions")

	def describe(self, node):
		return "%5.0fms|" % (node["during"]*1000)+ self.mark(node).format("", node["name"], node["description"], pad=node["depth"]*2)

	def tracked_stats(self):
		from .bdd import CONSTANTS as C
		return (
			Stat(lambda _: _.checkpoint().total_seconds()).called("during").type("numeric").aggregate_children(),
			#base test stats
			Stat(lambda _: _.succeeded).called("succeeded").type("numeric"),
			#composite test stats
			#because these no longer bubble, they're often 0, which can make division-by tests fail. unclear to me what a good fix is. Could maybe track one stat for local fail/succeed and another for cumulative descendant fail/succeed.
		)

	#the old logic here doesn't work, because we no longer accumulate failures/successes; anything that didn't explicitly fail/succeed should in theory end up yellow
	#TODO: a notion of incomplete failure (i.e., one but not all of my children failed)
	def mark(self, node):
		if node['succeeded'] == 0:
			return self.desc_str[0]
		elif node['succeeded'] == 1:
			return self.desc_str[1]
		else:
			return self.desc_str[2] #tests that didn't run (were skipped)
