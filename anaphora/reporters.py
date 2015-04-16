import sys
import colorama
from .stats import Stat

colorama.init(autoreset=True)


# stub that will remove colorama color codes for plaintext reporters
class NoOp(object):  # pylint: disable=too-few-public-methods
	def __getattr__(self, name):
		return ""


# base class for all reporters is uncolored
# This is just a dummy obj to replace colorama with to uncolor things
class ColorLlama(NoOp):  # pylint: disable=too-few-public-methods
	Fore = NoOp()
	Back = NoOp()
	Style = NoOp()


class Reporter(object):

	"""
	Base reporter class.

	The only strict requirements for subclasses is that they must:
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

	viz = ""

	def __init__(self, colorizer=colorama):
		try:
			self.register_format_strings(colorizer)
		except NotImplementedError:
			pass

	def color(self):
		self.register_format_strings(colorama)

	def uncolor(self):
		self.register_format_strings(ColorLlama)

	def report(self, testrun):
		raise NotImplementedError

	def register_format_strings(self, fmt):
		raise NotImplementedError

	def format_exception(self, exception):
		"""Return a string containing a single exception."""
		raise NotImplementedError

	@staticmethod
	def format_summary(node, runtime=None, exceptions=None):
		if exceptions is None:
			exceptions = node.db.exceptions(count=True)
		if runtime is None:
			runtime = node.db.execute("SELECT during FROM nodes where id=1;").fetchone()
		return "Anaphora run {:} in {:,.4f}s with {:} unignored exceptions.".format("failed" if exceptions else "passed", runtime, exceptions)

	@staticmethod
	def exit_status(exceptions):
		return 3 if exceptions else 0

	@staticmethod
	def tracked_stats():
		# LATERDO: this doc needs a rework, but it can wait until I decide if/how these additional stats make a return
		"""
		WARNING: This doc is obsolete, but it can't be rewritten until some other things are settled.
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

		See the stats.Stat class for a detailed discussion of how to compose stats and how they're computed.
		"""
		raise NotImplementedError

# LATERDO:
# class Minimal(Reporter):
# 	@classmethod
# 	def report(cls, run):
# 		exceptions = run.db.exceptions(count=True)
# 		print(cls.format_summary(run, exceptions=exceptions))


class Tree(Reporter):
	def register_format_strings(self, fmt):
		base = "{: <{pad}}{:}: {:}"
		self.desc_str = [
			fmt.Fore.RED + base,
			base,
			fmt.Fore.YELLOW + base,
			fmt.Fore.WHITE + base
		]
		# self.exception_str = '{cls}: {description}\n\nTraceback (most recent call last):\n\n  File "{file}", line {line}, in {context}\n    {code}\n{status}{output}'
		self.viz = "  " + fmt.Back.RED + " " + fmt.Back.RESET + " "

	# LATERDO: give this method massively more authority in dictating format and reduce the role of the .traceback property on the exception
	def format_exception(self, exception):
		output = exception['e_output']
		output = '\n\nAdditionally, the following was captured from stdout:\n    {output}'.format(output="\n    ".join(output.splitlines())) if output else ''
		return '{message}\n{traceback}{output}\n'.format(message=exception['e_message'], traceback=exception['e_traceback'], output=output)

	def report(self, run):
		for index, node in enumerate(run.db.tree()):
			# 0 == implicit node wrapping full run
			if index == 0:
				runtime = node['during']
			if node["depth"] > 0:
				print(self.format_node(node))

		exceptions = 0
		for exception in run.db.exceptions():
			exceptions += 1
			print("{:=^50}".format(" Exception %d " % exceptions))
			print(self.format_exception(exception), file=sys.stderr)

		print(self.format_summary(run, runtime, exceptions))

		return self.exit_status(exceptions)

	def format_node(self, node):
		return "%5.0fms|" % (node["during"] * 1000) + self.mark(node).format("", node["name"], node["description"], pad=node["depth"] * 2)

	@staticmethod
	def tracked_stats():
		return (
			Stat(lambda _: _.runtime.checkpoint("during").total_seconds()).called("during").type("numeric").aggregate_children(),
			# base test stats
			Stat(lambda _: _.succeeded).called("succeeded").type("integer"),
			Stat(lambda _: _.ignored).called("ignore").type("integer"),
			# composite test stats
		)

	def mark(self, node):
		# print(list(node))
		# print((node['e_message'], node['ignore'], node['succeeded']))
		if node['succeeded'] == 0:
			if node['ignore'] == 1:
				return self.desc_str[3]
			return self.desc_str[0]
		elif node['succeeded'] == 1:
			return self.desc_str[1]
		else:
			return self.desc_str[2]  # not run (read: skipped)
