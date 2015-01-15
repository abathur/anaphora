import colorama, traceback
from .bdd import TestError
from types import MethodType

colorama.init(autoreset=True)
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
	bubbles = {}
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
		"""
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
		cumulative = self.cumulative_times(node)
		runtime = cumulative["total"]
		return "derpiary"
		#return "Run time: {:,.4f}ms or {:,.4f}ms/test; Time alottment (tests: {:.2%}, hooks: {:.2%}, anaphora:{:.2%})".format(runtime, runtime/(node.stats.failures+node.stats.successes), (runtime - cumulative["anaphora"] - cumulative["hook"])/runtime, cumulative["hook"]/runtime, cumulative["anaphora"]/runtime)

	def bubble(self, what):
		if what in self.bubbles:
			return True, self.bubbles[what]
		else:
			return False, None


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
	bubbles = {"exception": False}
	def register_format_strings(self, fmt):
		base = "{: <{pad}}{:}: {:}"
		self.desc_str = [fmt.Fore.RED+base, base, fmt.Fore.YELLOW+base]
		self.viz = "  "+fmt.Back.RED+" "+fmt.Back.RESET+" "

	def report(self, node):
		#print("A total of {:} exceptions")
		for child in node.children:
			self.node_tree(child, 0, 1)

		print("Errors:")
		for child in node.children:
			print(self.format_nested_exceptions(child))

		print(self.runtime_summary(node))

		print(self.test_stats(node))

	def mark(self, node):
		if node.stats.failed:
			return self.desc_str[0]
		elif node.stats.succeeded:
			return self.desc_str[1]
		else:
			return self.desc_str[2] # reserving this for an unrun test, though for now there's no such concept TODO: un-run tests can be kinda faked by raising an error in enter to skip the block.

	def describe(self, node, indent, wrap_at):
		return self.mark(node).format("", node.__class__.__name__, node.description, pad=indent*2)

	def node_tree(self, node, indent, depth=float("inf")):
		if depth > 1:
			print(self.describe(node, indent, 80))
			for child in node.children:
				self.node_tree(child, indent+1, depth-1)
		elif depth == 1:
			print(self.describe(node, indent, 80))
			print("{: >{pad}s}".format("...", pad=(indent+3)*2))
