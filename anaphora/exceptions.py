import traceback


# base exception types, not thrown
class AnaphoraException(Exception):
	pass


class TestRunException(AnaphoraException):
	CRITICAL = False

	_lineno = None
	_path = None
	_context = None  # LATERDO: figure out where to get this (<module> or <function> or whatever; somewhere on one of the various f_code objects proably)
	_cause = None
	_output = None
	_traceback = None

	node = None
	initialized = False

	# properties subclasses may want to define
	_problem = None  # like, in before hook, or in external executable

	def __init__(self, node, *args, **kwargs):
		self.node = node
		self._traceback = []
		super().__init__(*args, **kwargs)

	# === start property API === #
	@property
	def kind(self):
		if self.node:
			if self.node.ignored == 1:
				return "Ignored{:}".format(self.__class__.__name__)
		return self.__class__.__name__

	@property
	def problem(self):
		return self._problem

	@property
	def path(self):
		if not self._path and self.__traceback__:
			self._path = self.__traceback__.tb_frame.f_code.co_filename  # pylint: disable=no-member
		return self._path

	@property
	def line(self):
		if not self._lineno and self.__traceback__:
			self._lineno = self.__traceback__.tb_lineno  # pylint: disable=no-member
		return self._lineno

	@property
	def context(self):
		return self._context

	@property
	def output(self):
		return self._output

	@output.setter
	def output(self, value):
		self._output = value

	@property
	def traceback(self):
		return "\n".join(self._traceback)

	@property
	def exception(self):
		return self.traceback

	@property
	def location(self):
		return '{path}:{line}'.format(path=self.path, line=self.line)

	@property
	def issue(self):
		return '{node} has {problem} at {location}'.format(node=self.node, problem=self.problem, location=self.location)

	@property
	def message(self):
		return '{kind}: {issue}'.format(kind=self.kind, issue=self.issue)

	@property
	def terminal(self):
		if self.CRITICAL and (self.node.ignored or self.node.options.permissive):
			return False
		else:
			return True
	# === end property API === #

	def try_raise(self):
		if self.terminal:
			raise

	def initialize(self):
		self.initialized = True
		cause = self.__cause__
		if cause:
			stackfrom = -2
			stack = traceback.format_exception(cause.__class__, cause, cause.__traceback__)
			trace = cause.__traceback__

			while trace:
				blame = trace
				trace = trace.tb_next
				# print("tb: %s" % blame)
				# print("lineno %s" % blame.tb_lineno)
				# print("filename %s" % blame.tb_frame.f_code.co_filename)

			# print("", file=sys.stderr)
			# print("stack %s" % stack, file=sys.stderr)
			# print("", file=sys.stderr)
			# need the following; will any of these names clash?
			self._lineno = blame.tb_lineno
			self._path = blame.tb_frame.f_code.co_filename
			# print([stack[0]]+stack[stackfrom:])
			self._traceback += [stack[0]] + stack[stackfrom:]

	def with_cause(self, cause):
		self.__cause__ = cause
		self.initialize()
		return self

	def __str__(self):
		return self.message


class HookError(TestRunException):
	CRITICAL = True
	_problem = "broken hook"


# 'TestFailure: {node} has failed assertion at {filename}:{line}:'
class TestFailure(TestRunException):
	_problem = "failed assertion"


# 'BeforeHookError: {node} has broken before hook at {filename}:{line}:'
class BeforeHookError(HookError):
	_problem = "broken before hook"


# 'AfterHookError: {node} has broken after hook at {filename}:{line}:'
class AfterHookError(HookError):
	_problem = "broken after hook"


# 'TestError: {node} has broken test body at {filename}:{line}:'
class TestError(TestRunException):
	CRITICAL = True
	_problem = "broken test body"


# ~ (shouldn't ever get printed)
class SkipNode(TestRunException):
	_problem = "was skipped"


# LATERDO:
# * reporters should be able to handle most of the formatting for these (i.e., the fake reporter below needs to fall so tightly in line with real exceptions that it's plausible for them to do so.) The best version of this will require giving the reporter a swing at formatting every exception if it declares some function?
# * evaluate whether informally calling this "TestFailure" is going to cause problems (i.e., do I need to lie when I insert it into the db, as well?)
class CommandFailure(TestFailure):
	exit_status = None

	@property
	def kind(self):
		if self.node:
			if self.node.ignored == 2:
				return "TestWarning"
			elif self.node.ignored == 1:
				return "IgnoredTestFailure"
		return "TestFailure"

	@property
	def problem(self):
		return 'exit status {exit_status} for "{node.test}"'.format(node=self.node, exit_status=self.exit_status)

	@property
	def issue(self):
		return '{problem} in {node.parent} at {location}'.format(node=self.node, problem=self.problem, location=self.location)

	def initialize(self):
		return  # too cool for school

	def __init__(self, node, frame, output, exit_status):
		super().__init__(node)
		self._context = frame[3]
		self._lineno = frame[2]
		self._path = frame[1]
		self._output = output
		self.exit_status = exit_status
		self._traceback = ['Traceback (most recent call last):\n', '  File "{file}", line {line}, in {context}\n    {code}\n'.format(file=self._path, context=self._context, code="".join(frame[4]).strip(), line=self._lineno)]

	@property
	def exception(self):
		return '{message}\n\n{traceback}\n{node} exited with exit_status {exit_status}\noutput:{output}'.format(
			message=self.message,
			traceback=self.traceback,
			node=self.node,
			exit_status=self.exit_status,
			output=self.output
		)
