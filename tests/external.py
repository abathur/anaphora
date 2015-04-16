from anaphora import Noun

ANAPHORA = Noun("AnaphoraSingleton")

def i_swear_i_am_the_external_tests():
	return True

ANAPHORA.grammar(["bootstrap"])

with bootstrap("wow, much test"):
	with bootstrap("so external"):
		assert 1 == 1
	with bootstrap("very pass"):
		assert 2 == 2
