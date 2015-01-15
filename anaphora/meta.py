import json
try:
	with open("tdver.json", "r") as f:
		config = json.load(f)
except FileNotFoundError:
	config = {}
