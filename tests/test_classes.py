class JustMethods(object):
	def test1(self):
		assert 2 == 2

	def test2(self):
		assert 1 == 1

	def test3(self):
		assert 3 == 3


class MostlyMethods(object):
	test = 1
	def before_class_hook(self):
		pass

	def after_class_hook(self):
		pass

	def before_method_hook(self):
		self.test *= 100

	def after_method_hook(self):
		self.test /= 2

	def test1(self):
		assert self.test == 100

	def test2(self):
		assert self.test == 5000

	def test3(self):
		assert self.test == 250000


def ignore_this():
	assert 1 == 0
