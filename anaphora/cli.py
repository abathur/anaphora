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
		"""replace Noun.__exit__, handle errors, report, clean up."""
		self.run_hooks(self.AFTER)
		exit = 0
		if exception_value:
			if isinstance(exception_value, (KeyError, TypeError, ImportError)):
				#this net may prove slightly too broad
				import traceback
				out = ["This doesn't appear to be an Anaphora test file."]
				out += ["==================="] #TODO
				out += traceback.format_exception(exception_value.__class__, exception_value, exception_value.__traceback__, chain=True)
				out += ["==================="] #TODO
				#out +=
				#out += ["Anaphora encountered the above error which prevented a test from executing. Anaphora can treat this broken test as a simple test failure if run with the -p or --permissive flag."]
				exit = "\n".join(out)
			elif isinstance(exception_value, TestRunException):
				#still need to exit
				out = [""]
				out += ["==================="] #TODO
				out += [exception_value.traceback]
				out += ["==================="] #TODO
				#out += traceback.format_exception(e.__cause__.__class__, e.__cause__, e.__cause__.__traceback__, chain=True)
				out += ["Anaphora encountered the above error which prevented a test from executing. Anaphora can treat this broken test as a simple test failure if run with the -p or --permissive flag."]
				exit = "\n".join(out)
			else:
				#If for some reason there's an unexpected error floating up here, let's make sure we arent' swallowing it.
				print("Attencion!")
				raise exception_value
		else:
			self.db.update_node(self)
			exit = self.report()

		#self.clean_up()
		clean_up()
		if self.__dev_debug:
			self.__objgraphs()
		sys.exit(exit)

	#anaphora TODO: this may still not be right; it may also be possible to fold most of this into exit if done smrtly.
	def run(self):
		"""
		Run the test suite by importing the specified file.

		Note that while the module object is returned, there is no
		obvious use case for keeping the reference at this time.
		"""
		#TODO: for some reason if we specify .py this will still import the right file but then throw an error. bog.
		return __import__(self.options.file, {}, locals(), [], 0)

CLI = CliRun("ClientRun")

import datetime
def main():
	"""Execute the command-line client run."""
	with CLI as Anaphora:
		Anaphora.run()


