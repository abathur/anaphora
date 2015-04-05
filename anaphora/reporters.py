import colorama, traceback, sys
from .bdd import TestError
from types import MethodType
from .bdd import Stat

colorama.init(autoreset=True)

#TODO: say what? was this just for debug?
# def noneprint(arg):
# 	if arg == None:
# 		traceback.print_stack()
# 	else:
# 		oldprint(arg)
# oldprint = print
# print = noneprint

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

	2. implement a register_format_strings function which accepts a formatter argument.
	The user is free to do nothing with this function if they wish, but users are
	encouraged to build all static information into their format strings only once;
	this method is only recycled if color/uncolor are called.

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

	def uncolor(self):
		global ColorLama
		self.register_format_strings(ColorLlama)

	def report(self, testrun):
		raise NotImplementedError

	def register_format_strings(self, fmt): #self, fmt
		raise NotImplementedError

	def format_exception(self, exception):
		"""Return a string containing a single exception."""
		return "{:=^80}\n{:}".format(str(exception[1].node), "".join(self.format_test_exception(exception)))

	@staticmethod
	def format_summary(node, runtime=None, exceptions=None):
		if exceptions == None:
			exceptions = node.db.exceptions(count=True)
		if runtime == None:
			runtime = node.db.execute("SELECT during FROM nodes where id=1;").fetchone()
		return "Test run {:} in {:,.4f}s with {:} unignored exceptions.".format("failed" if exceptions else "passed", runtime, exceptions)

	@staticmethod
	def exit_status(exceptions):
		return 3 if exceptions else 0

	def tracked_stats(self):
		"""Must return a tuple of stats this reporter wants tracked."""
		raise NotImplementedError

	@staticmethod
	def tracked_stats(self):
		#TODO ?
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
	@classmethod
	def report(cls, run):
		exceptions = run.db.exceptions(count=True)
		print(cls.format_summary(run, exceptions=exceptions))

class Tree(Reporter):
	#storing possibly useful tidbits commented out
		# print(run.db.execute("SELECT * FROM nouns;").fetchall())
		# print([dict(x) for x in run.db.execute("SELECT * FROM nodes WHERE description LIKE '%test%';").fetchall()])
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
		#print(dict(run.db.depths()))
		#print(dict(run.db.execute("SELECT sum()")))
		# print(dict(run.db.depth(2)))
		# print(dict(run.db.node(2)))
		# print(dict(run.db.depths(node_id=2)))
		# print(run.db.depths(node_id=2).fetchall())
		# print(dict(run.db.execute("SELECT sum(failures) FROM nodes;").fetchone()))
		# #print("A total of {:} exceptions")
		# 			# if node["e_message"]:
			# 	print("exception on this node")
	#end tidbits

	def register_format_strings(self, fmt):
		base = "{: <{pad}}{:}: {:}"
		self.desc_str = [fmt.Fore.RED+base, base, fmt.Fore.YELLOW+base, fmt.Fore.WHITE+base]
		self.exception_str = fmt.Back.WHITE+"{:}"+fmt.Back.RESET+"\n" # "{:=^10}".format("penis")
		self.viz = "  "+fmt.Back.RED+" "+fmt.Back.RESET+" "

	@staticmethod
	def format_exception(exception):
		return exception['e_traceback']

	def report(self, run):
		#do something meaningful with all of our nodes
		for index, node in enumerate(run.db.tree()):
			# 0 == whole run; just compile overall things here.
			if index == 0:
				runtime = node['during']
			if node["depth"] > 0:
				print(self.format_node(node))

		exceptions = 0
		#do something meaningful with our exceptions
		#TODO: this printing fucking sucks; change back to exceptions to debug
		for exception in run.db.exceptions():
			exceptions += 1
			print("{:=^50}".format(" Exception %d " % exceptions))
			print(self.format_exception(exception), file=sys.stderr)

		print(self.format_summary(run, runtime, exceptions))

		return self.exit_status(exceptions)

	def format_node(self, node):
		return "%5.0fms|" % (node["during"]*1000)+ self.mark(node).format("", node["name"], node["description"], pad=node["depth"]*2)

	@staticmethod
	def tracked_stats():
		from .bdd import CONSTANTS as C
		return (
			Stat(lambda _: _.checkpoint().total_seconds()).called("during").type("numeric").aggregate_children(),
			#base test stats
			Stat(lambda _: _.succeeded).called("succeeded").type("integer"),
			Stat(lambda _: _.ignored).called("ignore").type("integer"),
			#composite test stats
			#because these no longer bubble, they're often 0, which can make division-by tests fail. unclear to me what a good fix is. Could maybe track one stat for local fail/succeed and another for cumulative descendant fail/succeed.
		)

	def mark(self, node):
		if node['succeeded'] == 0:
			if node['ignore'] == 1:
				return self.desc_str[3]
			return self.desc_str[0]
		elif node['succeeded'] == 1:
			return self.desc_str[1]
		else:
			return self.desc_str[2] #tests that didn't run (were skipped)
