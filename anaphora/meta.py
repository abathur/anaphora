import json


class AttrDict(dict):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.__dict__ = self


class Config(AttrDict):

	def __init__(self):
		super().__init__()
		try:
			with open("tdver.json", "r") as opts:
				self.update(json.load(opts))
		except FileNotFoundError:
			pass
