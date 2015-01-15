# I think this is an iterator
class TestRunner(object):
	"""
	We run some sub portion of classes and will probably be subclassed for each specific instance. Nonetheless, we have some stable behavior which can be recycled across instances.

	This might be ultimately still based on Idiom, or may suggest that some code here and in idiom might beg for being refactored out into a shared class for inheritance.
	"""

	def __init__(self, description, targets):
		self.description = description
		self.targets = self.parse_targets(targets)
		self.order = list(range(len(self.targets)))
		self.random() #default sort

	def __iter__(self):
		return self

	def __next__(self):
		#using whatever sort method is supplied
		if self.order is None:
			self.order = self.sort(self.sorter)
		if None:
			raise StopIteration
		return self.targets

	def parse_targets(self, glob):
		raise NotImplementedError("parse_targets needs to be implmented on any subclass")

	#I think the most ideal api for these is that they can be set at definition time and trickle down to all instances of the defined idiom unless they are overriden at usage time, or they can be defined at each instance. The default is probably the random order.
	#The result of each of these functions is probably that it creates a closure which it sets as the idioms' internal sort func.
	#
	#do they need to return anything? (oh, hey, this isn't actually a viable way to sort for this usage?)
	def random(self):
		"""randomize the running of the tests within if it makes sense"""
		def random_sort(objects):
			...
		self.sorter = random_sort
		return self

	def defined(self):
		"""run the tests in defined order if it makes sense"""
		def defined_sort(objects):
			...
		self.sorter = defined_sort
		return self

	def order(self, closure):
		"""sort the tests based on whatever the fuck this closure tells us"""
		self.sorter = closure
		return self

	def sort(self):
		self.sorter(self.targets)

import glob

# assumption: tests are run just by importing the file
class FileRunner(TestRunner):
	files = []
	def parse_targets(self, selectors):
		# TODO: actually sort...
		for selector in selectors:
			for x in glob.glob(glob):
				try:
					files.append(__import__(x))
				except ImportError:
					pass

# assumption: tests are run by importing each file in each directory
class DirectoryRunner(FileRunner):
	...

#assumption: we must import something, instantiate the class, and call any method matching a regex
class ClassRunner(TestRunner):
	...

#assumption: we must import something and call any method matching a regex
class FunctionRunner(TestRunner):
	...
