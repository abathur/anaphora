import inspect
import subprocess
import itertools
import sys
from anaphora import meta, exceptions
import anaphora.utils
from anaphora.stats import Stat
import anaphora.db


def convert(converter):
	"""Wrap module/class/func/method objects with a special node object."""
	def matching(func):
		def match(self, predicate=None):
			if predicate:
				self.les_iterables = (converter(obj) for key, obj in func(self) if predicate(key))
			else:
				self.les_iterables = (converter(obj) for key, obj in func(self))
			return self
		return match
	return matching


class RunnerMixin(object):

	"""
	Support functions for TestRunners.

	See the TestRunner class for details.
	"""

	before_ran = False
	output_start = 0
	trap = anaphora.utils.STDOUT_TRAP
	_modules = None
	_test = None
	les_iterables = None

	def load(self, module_strs):
		self._modules = module_strs
		self.les_iterables = map(Module, module_strs)
		self.before_run()
		return self

	def shell(self, shell_strs):
		self.les_iterables = map(Shell, shell_strs)
		self.before_run()
		return self

	def __iter__(self):
		self.before_run()
		return self

	def __next__(self):
		try:
			return next(self.les_iterables)
		except StopIteration:
			self.after_run()
			raise

	def collect_output(self):
		test = self.trap.output(self.output_start)
		return test

	def capture_output(self):
		self.output_start = self.trap.start()

	def release_output(self):
		self.trap.stop()

	def before_run(self):
		if self.before_ran:
			return
		if not self.id:
			self.__class__.id = self.db.add_noun(self.__class__)
		self.id = self.db.add_node(self)  # pylint: disable=invalid-name
		self.add()

		self.coverage.start()
		self.hooks.run(self.hooks.BEFORE)
		self.before_ran = True

	def after_run(self):
		self.hooks.run(self.hooks.AFTER)
		self.coverage.end()

		if self.succeeded is None:
			self.try_succeed()

		self.db.update_node(self)
		self.clean_up()

	def classes(self, predicate=None):
		self.les_iterables = itertools.chain(*map(lambda x: x.classes(predicate), self.les_iterables))
		return self

	def functions(self, predicate=None):
		self.les_iterables = itertools.chain(*map(lambda x: x.functions(predicate), self.les_iterables))
		return self

	def modules(self, predicate=None):
		self.les_iterables = itertools.chain(*map(lambda x: x.modules(predicate), self.les_iterables))
		return self

	def methods(self, predicate=None):
		self.les_iterables = itertools.chain(*map(lambda x: x.methods(predicate), self.les_iterables))
		return self


# LATERDO: pylint disable below
class Noun(RunnerMixin):  # pylint: disable=too-many-instance-attributes
	runtime = None
	hooks = None
	coverage = None
	environment = None

	description = None
	parent = None
	nouns = None

	succeeded = None
	ignored = 0
	options = None
	reporter = None

	id = None  # this gets assigned after we're inserted in the db.
	_current = []  # intentionally class global.

	def __init__(self, desc, before=None, after=None):
		self.runtime = anaphora.utils.RuntimeTracker()
		# LATERDO: I hate doing config like this, but it's on the right track.
		if self.db is None:
			self.config(meta.Config())
		self.parent = self.current
		self.description = desc
		self.exceptions = []
		self.nouns = []

		self.hooks = anaphora.utils.Hooks(before, after)
		self.coverage = anaphora.utils.Coverage()
		self.environment = anaphora.utils.EnvironmentalProtectionAgency()

	@property
	def current(self):
		if len(self._current):
			return self._current[-1]
		else:
			return None

	def add(self):
		# print("adding %s which has parent: %s" % (self, self.parent))
		self._current.append(self)

	def remove(self):
		self._current.pop()

	def grammar(self, names):
		for name in names:
			if isinstance(name, str):
				new_class = type(name, (Noun,), {})
				inspect.currentframe().f_back.f_locals[name] = new_class
				self.nouns.append(new_class)
			elif isinstance(name, Noun):
				self.nouns.append(name)

		return self

	@staticmethod
	def config(options):
		Noun.options = options
		# print((cls, cls.options), file=sys.stderr)
		anaphora.db.QueryAPI(options)

	@property
	def db(self):  # pylint: disable=invalid-name,no-self-use
		return anaphora.db.sql

	# LATERDO: ideally this whole process for handling hook errors would be able to do something smrt if there are multiple hook errors. It seems entirely plausible that a user could have three exit hooks which produce two separate errors; unless we just stop executing hooks as soon as one fails, we're going to miss some of these.
	def _handle_exit_hook(self, exc, kind):
		"""Return updated ExcInfo after consuming a hook error."""
		try:
			self.hooks.consume_error(kind, self)
		except exceptions.HookError as new_exc:
			self.coverage.end()
			self.exception(new_exc)
			if exc is None:

				exc = anaphora.utils.ExcInfo(self, new_exc)
			else:

				exc.update(new_exc)
			new_exc.try_raise()
		return exc

	def _handle_exit_hooks(self, exc):
		"""Return updated ExcInfo after running after hooks and consuming before/after errors."""
		exc = self._handle_exit_hook(exc, self.hooks.BEFORE)
		self.hooks.run(self.hooks.AFTER)
		exc = self._handle_exit_hook(exc, self.hooks.AFTER)
		return exc

	def _parse_exit_exception(self, exc):
		"""
		Return updated ExcInfo and skip after deciding how to handle the current exception.

		Basically, if exception is:
		- None: just return None, False
		- SkipNode: skip returns true
		- SystemExit: go ahead and exit
		- AssertionError:
			- upgrade to anaphora.exceptions.TestFailure,
			- add to exception log
			- update ExcInfo
		"""
		skip = False
		if exc is None:
			return exc, skip

		# block summary: If we have an exception, decide whether it requires skipping the node, exiting the entire program, raising (i.e., terminating the node), or converting simple assertion errors into test failures.
		if isinstance(exc.value, exceptions.SkipNode):
			exc = None
			skip = True
		elif exc.type == SystemExit:
			sys.exit(exc.value)
		elif isinstance(exc.value, AssertionError):
			exc.upgrade_to(exceptions.TestFailure)
			self.exception(exc.value)
		# any kind of anaphora exception being handed up from a child node
		elif isinstance(exc.value, exceptions.TestRunException):
			exc.value.try_raise()

		return exc, skip

	def __enter__(self):
		if not self.id:
			self.__class__.id = self.db.add_noun(self.__class__)

		self.id = self.db.add_node(self)

		self.environment.snapshot(inspect.currentframe())
		self.add()

		self.coverage.start()

		self.hooks.run(self.hooks.BEFORE)
		return self

	def __exit__(self, exc_type, exc_value, exc_tb):
		exc = anaphora.utils.ExcInfo(self, exc_value) if exc_type else None
		exc, skip = self._parse_exit_exception(exc)
		exc = self._handle_exit_hooks(exc)

		if skip:
			pass
		elif exc:
			self.fail()
			# if it IS a TestError (doesn't incl hook)
			if isinstance(exc.value, exceptions.TestError):
				if exc.value.terminal:
					return False
			# if it's NOT a test error
			elif not isinstance(exc.value, exceptions.TestRunException):
				exc.upgrade_to(exceptions.TestError)
				self.exception(exc.value)
				exc.value.try_raise()
		else:
			self.try_succeed()

		self.environment.restore()  # scrub namespace
		self.db.update_node(self)
		self.clean_up()
		return True

	def stat(self, name):
		return Stat.stat(name).compute(self)

	def clean_up(self):
		self.db.clean_up(self)
		self.remove()

	# LATERDO: since all of my binary fields that get databased should do this,
	# this should probably documented in a better more global place?
	# sqlite api converts True/False and returns 1/0 on query
	# so succeeded sticks to what the db wants instead of forcing a
	# conversion going in and another coming out
	# a skipped node will have a value of None, which the db api will preserve
	def try_succeed(self):
		"""Mark as succeeded if we haven't already failed."""
		if self.succeeded is not 0:
			self.succeeded = 1

	# stats
	def fail(self):
		"""Mark as failed regardless."""
		self.succeeded = 0

	def exception(self, exception):
		if not exception.initialized:
			exception.initialize()
		output = self.collect_output()
		if len(output) and not exception.output:
			exception.output = "\n".join(output)
		self.exceptions.append(exception)
		self.db.add_exception(self, exception)

	def __str__(self):
		return "%s(%s)" % (self.__class__.__name__, self.description)

	def report(self):
		if self.reporter:
			return self.reporter.report(self)
		else:
			return 'nein reportage'

	# "special" functions for controlling some specific tests
	def skip(self):
		"""Skip execution of a node."""
		raise exceptions.SkipNode(self)

	# parts of our own test suite must be able to "fail" to properly test parts
	# of Anaphora that deal with test failures. In order to pass our own test
	# suite, we have to be able to ignore these failures.
	def ignore(self):
		"""
		Node is executed and failure tracked, but node is marked as ignored.

		When using default reporters, failures on ignored nodes don't influence
		the run's exit status. This is intended to let us collect information
		from tests that aren't critical (for example, a linter that may require
		significant work to comply with).

		It's worth noting that custom reporters have complete control over whether
		they report ignored nodes or allow them to influence the run status.
		"""
		self.ignored = 1


def clean_up():
	anaphora.db.sql.clear_stats()
	anaphora.db.sql = None


class TestRunner(Noun):

	"""
	Scaffold for running other types of test within an Anaphora run.

	Broadly, this enables a few uses of Anaphora:
	1. Folding tests written before Anaphora was in use into Anaphora's structured approach.
	2. Architecting an Anaphora run that spans many types of test.
	"""

	runnable = False

	def __init__(self, test, *args, **kwargs):
		self.test = test
		name = ""
		if hasattr(test, "__module__"):
			name += test.__module__ + "."
		if hasattr(test, "__self__"):
			name += test.__self__.__class__.__name__ + "."
		name += test.__name__
		super().__init__(name, *args, **kwargs)

	def run(self, *args, **kwargs):
		self.before_run()
		ran = None

		# LATERDO: figure out how to use ExcInfo?
		try:
			ran = self.execute(*args, **kwargs)
			self.try_succeed()
		except exceptions.TestFailure as exc:
			self.exception(exc)
			exc.try_raise()
		except subprocess.CalledProcessError as exc:
			self.fail()
			raise exceptions.TestFailure(self).with_cause(exc) from exc
		except (AssertionError,) as exc:
			try:
				raise exceptions.TestFailure(self).with_cause(exc) from exc
			except exceptions.TestFailure as exc:
				self.exception(exc)
				exc.try_raise()
		except Exception as exc:  # pylint: disable=broad-except
			# LATERDO: this is hungry; it eats all errors and won't help us debug any coding errors in external tests; should it be tightened?s
			try:
				raise exceptions.TestError(self).with_cause(exc) from exc
			except exceptions.TestError as exc:
				self.exception(exc)
				exc.try_raise()
		finally:
			self.after_run()

		return ran

	def execute(self, *args, **kwargs):
		raise NotImplementedError


class Callable(TestRunner):
	runnable = True

	def execute(self, *args, **kwargs):
		return self.test(*args, **kwargs)


class Function(Callable):
	pass


class Method(Callable):
	pass


class Class(TestRunner):
	@property
	def test(self):
		return self._test

	@test.setter
	def test(self, value):
		self._test = value()

	@convert(Method)
	def methods(self):  # pylint: disable=arguments-differ
		return inspect.getmembers(self.test, inspect.ismethod)

	def execute(self, *args, **kwargs):
		raise NotImplementedError


class Module(TestRunner):

	runnable = True

	def __init__(self, module_str, *args, **kwargs):
		self.delay_init = module_str
		self.lazy_constructor = self._construct()
		super(TestRunner, self).__init__("", *args, **kwargs)  # pylint: disable=bad-super-call

	@property
	def test(self):
		return next(self.lazy_constructor)

	@test.setter
	def test(self, value):
		self._test = value

	def construct(self):
		temp = __import__(self.delay_init, {}, None, [1], 0)
		self.test = temp
		self.description = temp.__name__
		del self.delay_init

	def _construct(self):
		self.construct()
		while True:
			yield self._test

	def execute(self, *args, **kwargs):
		return self.construct()

	@convert(lambda x: Module(x))  # pylint: disable=unnecessary-lambda
	def modules(self):  # pylint: disable=arguments-differ
		return inspect.getmembers(self.test, inspect.ismodule)

	@convert(Class)
	def classes(self):  # pylint: disable=arguments-differ
		return inspect.getmembers(self.test, inspect.isclass)

	@convert(Function)
	def functions(self):  # pylint: disable=arguments-differ
		return inspect.getmembers(self.test, inspect.isfunction)


class Shell(TestRunner):
	runnable = True

	def __init__(self, test, *args, **kwargs):
		name = self.test = test
		super(TestRunner, self).__init__(name, *args, **kwargs)  # pylint: disable=bad-super-call

	def execute(self, *args, **kwargs):
		self.release_output()
		status, output = subprocess.getstatusoutput(self.test)

		if status:
			stack = inspect.stack()
			# we want the first frame that isn't in this file
			for frame in stack:
				if inspect.getfile(frame[0]) != inspect.getfile(stack[0][0]):
					self.exception(exceptions.ShellFailure(self, frame, output, status))
					self.fail()
					break
		self.capture_output()
		return status
