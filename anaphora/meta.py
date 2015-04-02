import json

#TODO does some of this abstract stuff need to get moved into a single file?
class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

config = AttrDict()

try:
	with open("tdver.json", "r") as f:
		config.update(json.load(f))
except FileNotFoundError:
	pass
