
# There are a few different models we can use to decide what tests to run:
# 1.) we guess by using a pattern and looking through directories.
# 2.) we guess a specific file or directory and force them to be willingly integrated
# 3.) rather than a command you use to run your tests, Anaphora is an agnostic wrapper for your tests which could ostensibly be run by any test runner (though we probably provide one) with the result being that we'd need a context manager for a general anaphora run and some sort of sense for how they get run. We can say explicit beats implicit, but is it a weakness that anaphora isn't going to be able to run the tests of a subproject/package if they are composed under a different scheme?
# 4.) Have a process for creating a config file that tells us what to run when we type anaphora in a given directory.

# I think the way I feel about this is that explicit really is better, especially when our big idea is that we are structuring our tests. So part of anaphora's job, then, is providing a framework for specifying all of our types of test. I need to be able to run my feature tests AND my bug tests AND my integration tests. I think the subtext here is that we probably want some explicit functions or context managers or handlers that say, for example, run the tests in all of these files, or run the tests in all of these directories. And we want these managers to be subject to the same ability to construct grammar on the fly in order to let users build the hierarchies they need.

# This may mean 'idiom', strictly speaking, isn't robust enough for my use. Or that idiom is still the primary unit, but that there are some subclasses of idiom for the express purpose of running external tests. Or perhaps the idiom is still the unit of structure, but there are just still some viable methods we can use to execute an array of tests under it.

# anaphora <test.py>

import argparse, sys
from .bdd import Noun, TestRunException, clean_up
from . import reporters

#cli-specific interface
class CliRun(Noun):
	"""
	Syntax parsing and error handling for running Anaphora at the command line.
	"""
	__dev_debug = False
	def __init__(self, desc, config=None):
		self.parser = argparse.ArgumentParser(description="TOBEDOBEDO", prog="anaphora", conflict_handler='resolve', formatter_class=argparse.RawDescriptionHelpFormatter) #TODO
		self.parser.add_argument("file")
		self.parser.add_argument("-p", "--permissive", action="store_true") #permit a test run with programming errors to continue
		#self.parser.add_argument("-a", "--archive", action="store_true") #TODO
		#self.parser.add_argument("-t", "--track", action="store_true") #TODO
		#self.parser.add_argument("-e", "--earmarks", action="store_true", nargs='?', default=sys.stdin) #TODO
		#TODO: option for how to treat exceptions
		#TODO: option for specifying a reporter
		#TODO: passing arbitrary flags to the reporter itself?
		#TODO: if the above, do reporters need namespacing?
		self.parser.set_defaults
		if not config:
			from .meta import config
		self.options.update(self.parser.parse_args().__dict__)
		super().__init__(desc)
		self.reporter = reporters.Tree()
		self.db.track_stats(self.reporter.tracked_stats())

	def __objgraphs(self):
		import objgraph
		print(objgraph.show_backrefs(objgraph.by_type("requirement"), filename='/home/anaphora/backrefs.png'))
		print(objgraph.show_backrefs(objgraph.by_type("Stat"), filename='/home/anaphora/statrefs.png'))
		print(objgraph.show_backrefs(objgraph.by_type("QueryAPI"), filename='/home/anaphora/dbrefs.png'))
		print(objgraph.show_backrefs(objgraph.by_type("Noun"), filename='/home/anaphora/nounrefs.png'))
		print(objgraph.show_refs(objgraph.by_type("Noun"), filename='/home/anaphora/nounrefs2.png'))

	def __exit__(self, exception_type, exception_value, tb):
		"""Wrap Noun.__exit__, handle errors, report, clean up."""
		super().__exit__(exception_type, exception_value, tb)
		exit = 0
		if exception_value:
			if isinstance(exception_value, (KeyError, TypeError, ImportError)):
				#this net may prove slightly too broad
				exit = "This doesn't appear to be an Anaphora test file."
				#still need to exit
				out = [""]
				out += ["==================="] #TODO
				out += exception_value.format_exception()
				out += ["==================="] #TODO
				#out += traceback.format_exception(e.__cause__.__class__, e.__cause__, e.__cause__.__traceback__, chain=True)
				#out += ["Anaphora encountered the above error which prevented a test from executing. Anaphora can treat this broken test as a simple test failure if run with the -p or --permissive flag."]
				exit = "\n".join(out)
			elif isinstance(exception_value, TestRunException):
				#still need to exit
				out = [""]
				out += ["==================="] #TODO
				out += exception_value.format_exception()
				out += ["==================="] #TODO
				#out += traceback.format_exception(e.__cause__.__class__, e.__cause__, e.__cause__.__traceback__, chain=True)
				out += ["Anaphora encountered the above error which prevented a test from executing. Anaphora can treat this broken test as a simple test failure if run with the -p or --permissive flag."]
				exit = "\n".join(out)
			else:
				#If for some reason there's an unexpected error floating up here, let's make sure we arent' swallowing it.
				raise exception_value
		else:
			self.report()
			if self.succeeded is not None:
				exit = self.succeeded
			#otherwise, we need to find some more specific way to specify that an exception shouldn't "count"
		clean_up()
		if self.__dev_debug:
			self.__objgraphs()
		sys.exit(exit) #never gunna get here

	#anaphora TODO: this may still not be right; it may also be possible to fold most of this into exit if done smrtly.
	def run(self):
		"""
		Run the test suite by importing the specified file.

		Note that while the module object is returned, there is no
		obvious use case for keeping the reference at this time.
		"""
		#TODO: turn this into a use of FileRunner?
		print(self.options.file)
		#TODO: for some reason if we specify .py this will still import the right file but then throw an error. bog.
		return __import__(self.options.file, {}, locals(), [], 0)

CLI = CliRun("ClientRun")

import datetime

def professor():
	start = datetime.datetime.utcnow()
	diff = datetime.timedelta()
	print("wut")
	with CLI as Anaphora:
		#raise Exception()
		Anaphora.run()
		print("est. exec")
		print(datetime.datetime.utcnow() - start)

def main():
	"""Execute the command-line client run."""
	# import profile
	# profile.runctx("professor()", locals(), globals())
	professor()
	# start = datetime.datetime.utcnow()
	# diff = datetime.timedelta()
	# print("wut")
	# with CLI as Anaphora:
	# 	#raise Exception()
	# 	Anaphora.run()
	# 	print("est. exec")
	# 	print(datetime.datetime.utcnow() - start)


