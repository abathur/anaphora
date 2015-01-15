import traceback, sys, inspect, datetime, sqlite3
from collections import defaultdict
import coverage
from anaphora import meta, cover

class CONSTANTS(object):
	# runtime keys
	BEFORE = 0
	AFTER = 1
	SETUP = 2
	DURING = 3
	TEARDOWN = 4

class AnaphoraError(Exception):pass
class TestRunError(AnaphoraError):
	def __init__(self, errmess, node):
		super().__init__(errmess % node)
		self.node = node
class HookError(TestRunError):pass
class BeforeHookError(HookError):pass
class AfterHookError(HookError):pass
class TestError(TestRunError):pass

class RuntimeStats(CONSTANTS):
	runtime = None
	_checkpoint = None
	exceptions = None
	successes = defaultdict(int)
	failures = defaultdict(int)
	succeeded = 0
	failed = 0
	db = sqlite3.connect(':memory:')

	#stat keys
	EXCEPTIONS = 0
	SUCCESSES = 1
	FAILURES = 2

	#exception keys
	EXCEPTION_TYPE = 0
	EXCEPTION_VALUE = 1
	EXCEPTION_TRACEBACK = 2
	EXCEPTION_LABELS = {EXCEPTION_TYPE: "exception type", EXCEPTION_VALUE: "exception value", EXCEPTION_TRACEBACK: "exception traceback"}

	STAT_LABELS = ["exceptions","successes","failures"]
	RUNTIME_LABELS = ["before","after","setup","during","teardown"]

	def __init__(self):
		self.runtime = [datetime.timedelta() for x in range(5)]
		self._checkpoint = datetime.datetime.utcnow()
		self.exceptions = []

	def checkpoint(self, name):
		self.runtime[name] = datetime.datetime.utcnow() - self._checkpoint
		self._checkpoint = datetime.datetime.utcnow()

	def succeed(self, name):
		self.successes[name] += 1
		self.succeeded += 1

	def fail(self, name):
		self.failures[name] += 1
		self.failed += 1

	def stats(self, verbose=False):
		"""Return a list or dict of our statistics."""
		if verbose:
			return {x:y for x,y in zip([self.exceptions, self.successes, self.failures], self.STAT_LABELS)}
		else:
			return [self.exceptions, self.successes, self.failures, self.succeeded, self.failed]

	def runtimes(self, verbose=False):
		"""Return a list (optionally a dict) of runtimes in float seconds."""
		if verbose:
			return {x.total_seconds():y for x,y in zip(self.runtime, self.RUNTIME_LABELS)}
		else:
			return [x.total_seconds() for x in self.runtime]

	def hook_overhead(self):
		return self.runtime[self.BEFORE].total_seconds() + self.runtime[self.AFTER].total_seconds()

	def anaphora_overhead(self):
		return self.runtime[self.SETUP].total_seconds() + self.runtime[self.TEARDOWN].total_seconds()

	def test_time(self):
		self.runtime[self.DURING].total_seconds()

	def run_time(self):
		return sum(self.runtimes())
"""
	terms:
	hook overhead = tover = before hooks, after hooks
	anaphora overhead = fover = setup, teardown or sum - before/after hooks and during

	There are a lot of ways to give any detail on runtime:
	- sum(runtimes); this includes time we waste and time you waste
	- sum(runtimes) (%overhead)
	- sum(runtimes) (overhead)
	- during + sum(before, after, setup, teardown (collectively "overhead"))
	- ...

	So perhaps it's better to think in terms of what this information would give me and the scenarios under which I want it. I want to know how long my tests take to run in total, and I want to know where there are slow tests. And when there are slow test trees, I want a sense of how much of the time spent there I am responsible for (i.e., what portion I can actually save myself, and what portion is hidden in the framework.)
	"""

class Noun(CONSTANTS):
	description = None
	environment_vars = None
	environment_var_keys = None
	hooks = None
	parent = None
	children = None
	nouns = None
	coverage = None
	done = False
	hook_error = None
	hook_error_type = None
	_current = [] #intentionally shared for class instances.

	def __init__(self, desc, *args, **kwargs):
		self.parent = self.current
		self.description = desc
		self.exceptions = []
		self.children = []
		self.nouns = []
		self.coverage = {}
		self.stats = RuntimeStats()

		self.hooks = {self.BEFORE:[], self.AFTER:[]}
		if 'before' in kwargs:
			self.hooks[self.BEFORE].append(kwargs['before'])
		if 'after' in kwargs:
			self.hooks[self.AFTER].append(kwargs['after'])
		if 'options' in kwargs:
			self.options = kwargs['options']
		if 'config' in kwargs:
			self.config = kwargs['config']

	@property
	def current(self):
		if len(self._current):
			return self._current[-1]
		else:
			return None

	def add(self):
		if self.parent:
			self.parent.children.append(self)

		self._current.append(self)

	def remove(self):
		self.done = True
		self._current.pop()

	def grammar(self, names):
		for name in names:
			if isinstance(name, str):
				new_class = type(name, (Noun,), {})
				inspect.currentframe().f_back.f_locals[name] = new_class #TODO: should this be f_locals or f_globals?
				self.nouns.append(new_class)
			elif isinstance(name, Noun):
				self.nouns.append(name)

		return self
		#noun


	def config(self, config, options):
		self.config = config
		self.options = options

	def __enter__(self):
		self.environment_vars = inspect.currentframe().f_back.f_locals
		# this needs to get moved off into a branch in case we need it
		# self.environment_vars['this'] = self
		self.environment_var_keys = set(self.environment_vars.keys())
		self.add()
		#self.cov = coverage.coverage(branch=True, omit="*anaphora/__init__.py")#, , omit=["test.py", "*colorama*"]plugins=["plugin"]
		# in the cli model this is parsed out of the command options...
		# print(__file__)
		self.cov = coverage.coverage(branch=True)
		#self.cov = coverage.coverage(branch=True, omit=[__file__, "*anaphora/__init__.py"])
		#self.cov = coverage.coverage(branch=True, omit=["*%s.py" % self.options.file, "*anaphora/__init__.py"])
		self.cov.start()

		self.stats.checkpoint(self.SETUP)
		# we are now on the *user's* time, be fleet of foot

		try:
			self.run_hooks(self.BEFORE)
		except Exception as e:
			# we can't raise an error here or it'll terminate our with statement and send
			# the error up to our parent's __exit__ func; but we still need the error, so
			# we'll save it and use it in our own exit func later.
			self.hook_error_type = self.BEFORE
			self.hook_error = e

		self.stats.checkpoint(self.BEFORE)
		return self

	"""
	What is the desired hook failure mode? it seems like our goals should be:
	1.) that test doesn't execute (this actually isn't practical unless we actually raise an error, yeah?)
	2.) the outer test either continues, or halts; ideally anything that doesn't DEPEND on the failing test can go ahead and anything that does shouldn't run. But we don't have any real clear way of specifying when something does/n't depend. It makes little sense to test a feature that relies on another feature test that has already failed.

	python's unittest module handles this concept in the setup/teardown funcs; principle of least-surprise may dictate I take a similar tack:
	setUp()¶
		Method called to prepare the test fixture. This is called immediately before calling the test method; other than AssertionError or SkipTest, any exception raised by this method will be considered an error rather than a test failure. The default implementation does nothing.

	tearDown()
		Method called immediately after the test method has been called and the result recorded. This is called even if the test method raised an exception, so the implementation in subclasses may need to be particularly careful about checking internal state. Any exception, other than AssertionError or SkipTest, raised by this method will be considered an error rather than a test failure. This method will only be called if the setUp() succeeds, regardless of the outcome of the test method. The default implementation does nothing.
	"""
	#TODO has this partial rewrite introduced problems in where checkpoints are located?
	def __exit__(self, exception_type, exception_value, tb):
		self.stats.checkpoint(self.DURING)

		if exception_type is not None:
			if exception_type == SystemExit:
				sys.exit(exception_value)
			elif exception_type != AssertionError:
				print(exception_type, exception_value, tb)
				sys.exit("Uncaught, unexpected exception during test run, somehow...")

		# there was an error in a before hook, so we'll create a hook error based on it
		# and add it to the list of exceptions for this node
		if self.hook_error_type == self.BEFORE:
			try:
				raise BeforeHookError("Error in before hook of %s:", self) from self.hook_error
			except BeforeHookError:
				self.exception(sys.exc_info())

		try:
			self.run_hooks(self.AFTER)
		except Exception as e:
			self.hook_error_type = self.AFTER
			# there was an error in an after hook, so we'll create a hook error based on it
			# and add it to the list of exceptions for this node
			try:
				raise AfterHookError("Error in after hook of %s:", self) from e
			except AfterHookError:
				self.exception(sys.exc_info())

		self.stats.checkpoint(self.AFTER)
		if self.hook_error_type != None:
			self.cov.stop()
			self.cov.save()
			reporter = cover.Dict(self.cov, self.cov.config)
			self.coverage = reporter.statistics(None)

		self.remove()

		#TODO: only nodes with no children actually "succeed" or "fail"? (they get double-counted otherwise and totals become useless, but this isn't strictly true since an encompassing block can certainly have test conditions of its own...)
		if not len(self.children):
			if exception_type is not None:
				self.fail()

				#chain an error off the actual exception to add value
				try:
					raise TestError("Error in body of %s:", self) from exception_value
				except TestError:
					self.exception(sys.exc_info())
			elif self.hook_error:
				self.fail()
			else:
				self.succeed()

		#clean up anything we've added to the namespace
		for x in (self.environment_vars.keys() - self.environment_var_keys):
			del self.environment_vars[x]

		self.stats.checkpoint(self.TEARDOWN)
		return True

	def bubble(self, what):
		"""
		Return True if a reporter along the chain wants us to bubble <what>.

		If no one says a word, our default is to bubble.
		"""
		each = self
		while each.parent:
			each = each.parent
			if hasattr(each, 'reporter'):
				reporter_cares, reporter_wants = each.reporter.bubble(what)
				if reporter_cares:
					return reporter_wants

		return True

	def cascade(f):
		def uphill(self, *args, **kwargs):
			if self.parent:
				if self.bubble(f.__name__):
					getattr(self.parent, f.__name__)(*args, **kwargs)
			f(self, *args, **kwargs)
		return uphill

	#noun
	@cascade
	def succeed(self):
		self.stats.succeed(self.__class__.__name__)
	#noun
	@cascade
	def fail(self):
		self.stats.fail(self.__class__.__name__)

	#noun
	@cascade
	def exception(self, exception):
		self.stats.exceptions.append(exception)

	def __str__(self):
		return "%s: %s" % (self.__class__.__name__, self.description)

	def run_hooks(self, kind):
		for hook in self.hooks[kind]:
			hook(self)

Anaphora = Noun("AnaphoraSingleton")
