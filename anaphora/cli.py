
# There are a few different models we can use to decide what tests to run:
# 1.) we guess by using a pattern and looking through directories.
# 2.) we guess a specific file or directory and force them to be willingly integrated
# 3.) rather than a command you use to run your tests, Anaphora is an agnostic wrapper for your tests which could ostensibly be run by any test runner (though we probably provide one) with the result being that we'd need a context manager for a general anaphora run and some sort of sense for how they get run. We can say explicit beats implicit, but is it a weakness that anaphora isn't going to be able to run the tests of a subproject/package if they are composed under a different scheme?
# 4.) Have a process for creating a config file that tells us what to run when we type anaphora in a given directory.

# I think the way I feel about this is that explicit really is better, especially when our big idea is that we are structuring our tests. So part of anaphora's job, then, is providing a framework for specifying all of our types of test. I need to be able to run my feature tests AND my bug tests AND my integration tests. I think the subtext here is that we probably want some explicit functions or context managers or handlers that say, for example, run the tests in all of these files, or run the tests in all of these directories. And we want these managers to be subject to the same ability to construct grammar on the fly in order to let users build the hierarchies they need.

# This may mean 'idiom', strictly speaking, isn't robust enough for my use. Or that idiom is still the primary unit, but that there are some subclasses of idiom for the express purpose of running external tests. Or perhaps the idiom is still the unit of structure, but there are just still some viable methods we can use to execute an array of tests under it.

# anaphora <test.py>

import argparse
from .bdd import Noun
from . import reporters

#cli-specific interface
class CliRun(Noun):
	def __init__(self, desc, config=None):
		self.parser = argparse.ArgumentParser(description=__doc__, prog="anaphora", conflict_handler='resolve', formatter_class=argparse.RawDescriptionHelpFormatter)
		self.parser.add_argument("file")
		self.parser.set_defaults
		if not config:
			from meta import config
		super().__init__(desc, config=config, options=self.parser.parse_args())
		self.reporter = reporters.Tree()

	#anaphora TODO: this may still not be right
	def run(self):
		try:
			self.test = __import__(self.options.file, {}, locals(), [], 0)
		except (KeyError, TypeError, ImportError) as e:
			print(e)
			import sys
			sys.exit("This doesn't appear to be an Anaphora test file.")
			# or even a valid python file; do I need to be more specific?


Anaphora = CliRun("AnaphoraSingleton")

def main():
	with Anaphora as blerp:
		blerp.run()
	blerp.reporter.report(blerp)
	#TODO would it be kinda nice to know this at start so we can skip collecting these when they aren't going to get used? In a reporter-class model, the reporter needs to be queryable for what it would want us to collect.
