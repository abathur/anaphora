import datetime
import sys
from collections import defaultdict
from io import StringIO
from packaging.specifiers import SpecifierSet

from anaphora import exceptions


# Adapted from code by Oren Tirosh, MIT license per http://code.activestate.com/recipes/578231-probably-the-fastest-memoization-decorator-in-the-/
class CacheDict(dict):

    """
    Memoize calls to a closure provided on init which accepts a single argument.
    """

    def __init__(self, func):
        self.func = func
        super().__init__()

    def __missing__(self, key):
        ret = self[key] = self.func(key)
        return ret


class MemoizedSpecifierSet(SpecifierSet, CacheDict):
    def __init__(self, specifier):
        SpecifierSet.__init__(self, specifier)
        CacheDict.__init__(self, self.contains)


class Earmarks(CacheDict):
    def __init__(self, options):
        self.options = options
        super().__init__(MemoizedSpecifierSet)

    def __call__(self, specifier):
        return self[specifier][self.options.earmarks]


class CaptureOutput(list):

    """Suppress stdout but keep the output accessible."""

    _stdout = _stringio = None
    capturing = False

    def start(self):
        """Start capturing stdout and return present line number."""
        if not self.capturing:
            self._stdout = sys.stdout
            sys.stdout = self._stringio = StringIO()
            self.capturing = True
        return len(self)

    def stop(self):
        """Stop capturing stdout."""
        if self.capturing:
            self.extend(self._stringio.getvalue().splitlines())
            sys.stdout = self._stdout
            self.capturing = False

    def output(self, start):
        """Return all cached output after <start>."""
        if self.capturing:
            self.extend(self._stringio.getvalue().splitlines())
            sys.stdout = self._stringio = StringIO()
        out = self[start:]
        del self[start:]
        return out


STDOUT_TRAP = CaptureOutput()


class Hooks(defaultdict):
    BEFORE = 0
    AFTER = 1
    GENERAL = 2
    EXCEPTIONS = {
        BEFORE: exceptions.BeforeHookError,
        AFTER: exceptions.AfterHookError,
        GENERAL: exceptions.HookError,
    }
    errors = None

    def __init__(self, before, after):
        super().__init__(list)
        self.errors = defaultdict(list)
        if before:
            self[self.BEFORE].append(before)
        if after:
            self[self.AFTER].append(after)

    def add(self, kind, hook):
        self[kind].append(hook)

    def run(self, kind):
        for hook in self[kind]:
            try:
                hook(self)
            except Exception as exc:  # pylint: disable=broad-except
                # squelch error but save it for the consumer to handle
                self.errors[kind].append(exc)

    def consume_error(self, kind, node):
        """Raise the last recorded hook error of <kind>, or do nothing."""
        if len(self.errors[kind]):
            old_err = self.errors[kind].pop()
            new_err = None
            if kind in self.EXCEPTIONS:
                new_err = self.EXCEPTIONS[kind]
            else:
                new_err = self.EXCEPTIONS[self.GENERAL]

            raise new_err(node).with_cause(old_err) from old_err


class Coverage(object):
    coverage = None

    def __init__(self):
        # LATERDO: will be interesting to figure out how to db this, perhaps it can wait
        # coverage stats disabled for now
        # self.coverage = {}
        pass

    def start(self):  # pylint: disable=no-self-use
        return
        # self.cov = coverage.coverage(branch=True)
        # self.cov.start()
        # LATERDO: turn coverage back on?
        # self.cov = coverage.coverage(branch=True, omit="*anaphora/__init__.py")#, , omit=["test.py", "*colorama*"]plugins=["plugin"]
        # in the cli model this is parsed out of the command options...
        # print(__file__)
        # self.coverage.start()
        # self.cov = coverage.coverage(branch=True)
        # self.cov = coverage.coverage(branch=True, omit=[__file__, "*anaphora/__init__.py"])
        # self.cov = coverage.coverage(branch=True, omit=["*%s.py" % self.options.file, "*anaphora/__init__.py"])
        # self.cov.start()

    def end(self):  # pylint: disable=no-self-use
        return
        # self.cov.stop()
        # self.cov.save()
        # reporter = cover.Dict(self.cov, self.cov.config)
        # self.coverage = reporter.statistics(None)


# There's some reasonable debate about whether this should attempt to rollback other namespace changes, but for now it just kills anything added after we started
class EnvironmentalProtectionAgency(object):
    values = None
    keys = None

    def snapshot(self, frame):
        self.values = frame.f_back.f_locals
        self.keys = set(self.values.keys())

    def restore(self):
        for var in self.values.keys() - self.keys:
            del self.values[var]


class RuntimeTracker(defaultdict):
    def __init__(self, track=None):
        """Setup default timer and any additional timer names specified in <track>."""
        self.timers = defaultdict(datetime.datetime.utcnow)
        starttime = self.start()  # start the default timer (timers[None])
        for timer in track or []:
            self.timers[timer] = starttime
        super().__init__(datetime.timedelta)

    def reset(self):
        self.clear()
        self.timers.clear()

    def start(self, timer=None):
        """Start a timer and return the time at which it was started."""
        return self.timers[timer]

    def stop(self, timer=None):
        """Remove a timer and return its present accumulated time."""
        return datetime.datetime.utcnow() - self.timers.pop(timer)

    def checkpoint(self, name, previous=None, timer=None):
        """
        Save and return time accumulated in <timer> from <previous> checkpoint.

        If previous is unspecified, all accumulated time is returned.
        Checkpoint value remains accessible as self[name] unless overwritten.
        """
        temp = self[name] = self.check(previous=previous, timer=timer)
        return temp

    def check(self, previous=None, timer=None):
        """Return time accumulated in <timer> from <previous> checkpoint."""
        return datetime.datetime.utcnow() - self.timers[timer] - self[previous]


class ExcInfo(object):
    skip = trace = value = type = node = None

    def __init__(self, node, exc):
        self.node = node
        self.update(exc)

    def update(self, exc):
        self.type = exc.__class__
        self.value = exc
        self.trace = exc.__traceback__

    def upgrade_to(self, new_class):
        try:
            raise new_class(self.node).with_cause(self.value) from self.value
        except new_class as new_exc:
            self.update(new_exc)
