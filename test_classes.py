class JustMethods(object):
	def test1(self):
		assert 2 == 2

	def test2(self):
		assert 1 == 1

	def test3(self):
		assert 3 == 3


class MostlyMethods(object):
	test = 1
	def before_hook(self):
		self.test *= 100

	def after_hook(self):
		self.test /= 2

	def test1(self):
		print(self.test)
		assert self.test == 100

	def test2(self):
		print(self.test)
		assert 1 == 2
		assert self.test == 5000

	def test3(self):
		print(self.test)
		assert self.test == 250000


def ignore_this():
	assert 1 == 0
