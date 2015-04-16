"""Anaphora command-line interface."""
import sys
import argparse

from .meta import Config
from .exceptions import TestRunException
from . import reporters
from .runners import Noun, clean_up


class CliConfig(Config):
	def __init__(self):
		super().__init__()
		parser = argparse.ArgumentParser(description="Runner for anaphora test modules. See: docs", conflict_handler='resolve', formatter_class=argparse.RawTextHelpFormatter)
		parser.add_argument("module", help="Python module containing tests")
		#
		parser.add_argument("-p", "--permissive", action="store_true", help="count broken tests as simple test failures")
		# LATERDO: parser.add_argument("-e", "--earmarks", action="store_true", nargs='?', default=sys.stdin)
		save_choices = {
			"archive": "save with datestamp in file name",
			"replace": "save only most-recent run",
			"track": "Pending: save all runs in one db"
		}
		parser.add_argument("-s", "--save", choices=save_choices.keys(), help="save SQLite database containing the test results\n" + "\n".join([" - {:}\t{:}".format(key, value) for key, value in save_choices.items()]))
		self.update(parser.parse_args().__dict__)

# LATERDO: option for how to treat exceptions
# LATERDO: option for specifying a reporter
# LATERDO: passing arbitrary flags to the reporter itself?
# LATERDO: if the above, do reporters need namespacing?


class CliRun(Noun):

	"""Syntax parsing and error handling for running Anaphora on the command line."""

	__dev_debug = False

	def __init__(self, desc):
		self.config(CliConfig())
		super().__init__(desc)
		self.reporter = reporters.Tree()
		self.db.track_stats(self.reporter.tracked_stats())

	def __exit__(self, exception_type, exception_value, tb):
		"""replace Noun.__exit__, handle errors, report, clean up."""
		self.hooks.run(self.hooks.AFTER)
		out = 0
		if exception_value:
			if isinstance(exception_value, (KeyError, TypeError, ImportError)):
				# this net may prove slightly too broad
				import traceback
				out = ["This doesn't appear to be an Anaphora test file."]
				out += ["==================="]
				out += traceback.format_exception(exception_value.__class__, exception_value, exception_value.__traceback__, chain=True)
				out += ["==================="]
				# out +=
				# out += ["Anaphora encountered the above error which prevented a test from executing. Anaphora can treat this broken test as a simple test failure if run with the -p or --permissive flag."]
				out = "\n".join(out)
			elif isinstance(exception_value, TestRunException):
				out = [""]
				out += ["==================="]
				out += [exception_value.message]
				out += [exception_value.traceback]
				out += ["==================="]
				# out += traceback.format_exception(e.__cause__.__class__, e.__cause__, e.__cause__.__traceback__, chain=True)
				out += ["Anaphora encountered the above error which prevented a test from executing. Anaphora can treat this broken test as a simple test failure if run with the -p or --permissive flag."]
				out = "\n".join(out)
			else:
				# If for some reason there's an unexpected error floating up here, let's make sure we arent' swallowing it.
				print("Attencion!")
				raise exception_value
		else:
			self.db.update_node(self)
			out = self.report()

		# self.clean_up()
		clean_up()
		if self.__dev_debug:
			_objgraphs()
		sys.exit(out)

	def run(self):
		"""
		Run the test suite by importing the specified file.

		Note that while the module object is returned, there is no
		obvious use case for keeping the reference at this time.
		"""
		return __import__(self.options.module, {}, locals(), [], 0)


def main():
	"""Execute the command-line client run."""
	with CliRun("ClientRun") as anaphora:
		anaphora.capture_output()
		anaphora.run()
		anaphora.release_output()


def _objgraphs():
	import objgraph
	print(objgraph.show_backrefs(objgraph.by_type("requirement"), filename='/home/anaphora/backrefs.png'))
	print(objgraph.show_backrefs(objgraph.by_type("Stat"), filename='/home/anaphora/statrefs.png'))
	print(objgraph.show_backrefs(objgraph.by_type("QueryAPI"), filename='/home/anaphora/dbrefs.png'))
	print(objgraph.show_backrefs(objgraph.by_type("Noun"), filename='/home/anaphora/nounrefs.png'))
	print(objgraph.show_refs(objgraph.by_type("Noun"), filename='/home/anaphora/nounrefs2.png'))
