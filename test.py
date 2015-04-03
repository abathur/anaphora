from anaphora import Anaphora
assert Anaphora.exceptions == Anaphora.nouns == [], "Anaphora object should have no history, yet."

Anaphora.grammar(["boot"])

assert Anaphora.nouns == [boot], "Anaphora object should have exactly one noun."
Anaphora.grammar(["strap"])

# boot should only test major structural parts of the module that
# must work for the rest of the tests to function.
with boot("make sure we can configure Anaphora") as bootstrap:

	#implied test of nesting Nouns
	with strap("make sure we can use existing idioms"):
		#the very fact we haven't failed seems to prove this
		assert 1 == 1
		#assert isinstance(bootstrap.children[0], strap) #not sure offhand

	with strap("make sure we can create fresh/local nouns"):
		bootstrap.grammar(["foo", "bar"])
		assert foo
		assert bar
		assert bootstrap.nouns == [foo, bar]

		with foo("use them to capture an error...") as child1:
			#intentional error
			assert len(child1.exceptions) == 1, "We shouldn't have any errors yet" # TODO: CHECK STATS

		with bar("and continue execution") as child:
			assert 1 == 1
			#assert child1.succeeded == False, "We should already have exactly one error." # TODO: CHECK STATS

	with strap("and clean up after ourselves"):
		# this _could_ be a false promise, since the objects we're using are accumulating data, and the user could theoretically run into problems where they assume that state won't persist and it will. For example, what if they decide to rework the rules of one of their grammatical units midway through the test to support a special block (i.e., every "need" idiom runs with a special before/after hook), and expect those idioms to return to normal functioning outside of those blocks?
		# Likewise, they could create an object for their own purpose in a parent block, change its state in some way in a nested/child section, and expect that state change not to be visible within a sibling/peer of the nested/child block.
		# If this becomes a bridge we have to cross, it's likely we'll need to make them specify this behavior on the idiom; an idiom in loose cleanup mode just removes completely new additions to the namespace, while an idiom in strict cleanup mode saves a copy of the namespace on entry to which we are reset on each exit.

		assert 'foo' not in locals(), "Local 'foo' wasn't cleaned up."
		assert 'bar' not in locals(), "Local 'bar' wasn't cleaned up."
		#assert len(bdd.this.idioms) == 0, "Changes to local bdd.anaphora--should they be cleaned up?"

#this currently doesnt get tracked right
assert "bootstrap" not in locals(), "bootstrap should've been killed."

del boot
del strap
Anaphora.nouns = []
Anaphora.grammar(["app"])

with app("Anaphora").grammar(["need", "goal", "requirement"]):
	with need("customize tests with before/after hooks"):
		i = 0
		def test_hook(node):
			global i
			i += 10
		def terminal_hook(node):
			def shit():
				def fuck():
					def me():
						raise IOError
					me()
				fuck()
			shit()
			raise IOError

		with goal("register successful before hook", before=test_hook) as this:
			assert len(this.hooks[this.BEFORE]) == 1, "No before hook registered."
			with requirement("before hook executes successfully"):
				assert i == 10, "Before hook failed to run successfully."

		with goal("register successful after hook", after=test_hook) as this:
			assert len(this.hooks[this.AFTER]) == 1, "No after hook registered."

		with requirement("hooks execute successfully"):
			# we're testing that both the before and after hook executed.
			assert i == 20, "Hooks failed to run successfully."

		with goal("hook failures are properly tracked") as tracker:
			with requirement("before hook failure is tracked", before=terminal_hook) as this:
				def fuck():
					def me():
						def so():
							def fucking():
								def hard():
									assert 0 == 1
								hard()
							fucking()
						so()
					me()
				fuck()
				assert 0 == 1
				assert this.hook_error != this.BEFORE, "Before hook failure not tracked"
			with requirement("after hook failure is tracked", after=terminal_hook) as this:
				tracker.after = this
			assert tracker.after.hook_error == tracker.after.AFTER

	with need("queryable testing statistics") as parent:
		with goal("track runtime"):
			with requirement("start has been set") as this:
				assert this.checkpoint is not None, "node has no tracked time checkpoint." # TODO: CHECK STATS

			def after(node):
				import datetime
				assert node.runtime[node.DURING] > datetime.timedelta(), "node has no tracked runtime." # TODO: CHECK STATS

			with requirement("runtime has accumulated", after=after):
				import uuid
				for x in range(1000):
					uuid.uuid4()


		with goal("count successes/failures") as child:
			_.skip()
			assert child.successes == 0, "We should have no local successes." # TODO: CHECK STATS
			assert Anaphora.failures == 1, "Previous local failure not recorded." # TODO: CHECK STATS
			assert Anaphora.successes == 12, "Previous global success not recorded." # TODO: CHECK STATS

	with need("queryable coverage statistics"):
		with goal("coverage statistics are computed as tests run"):
			with requirement("anaphora's files only get included "
				"when they are being intentionally tested"):
				...
			with requirement("stubbeh"):
				...
		with goal("coverage statistics may be queried after tests run"):
			... #this is an absurd thing to test, no?

	# implicit test of the batch randomizer
	with need("integrate other types of tests with anaphora run"):
		with goal("run test functions from additional modules"):

			wert = 9
			for func in goal("run all functions").load(["test3"]).functions():
				#print("wert: %s" % wert)
				wert = func.run(wert)
			assert wert == 5, "Imported functions didn't run successfully."

			for func in goal("run just functions matching a predicate").load(["test3"]).functions(lambda x: x == "test2"):
				#print(func.parent)
				wert = func.run(wert)
			assert wert == 10, "Imported function didn't run successfully."

		with goal("run test methods on additional classes"):
			# for method in goal("run all methods").load(["test_classes"]).classes().methods():
			# 	method.run()
			for cls in goal("run all methods indiscriminately").load(["test_classes"]).classes(lambda x: x == "JustMethods"):
				#here we also kinda expect us to enter "cls" structurally, but this is neither a CM nor an iterator on cls, so we don't.
				#print("cls.parent:%s" % cls.parent)
				for method in cls.methods():
					#and then because we never "entered" cls before, when we call cls as an iterator here, we finally enter it?
					#print("method.parent:%s" % method.parent)
					#print("cls.parent:%s" % cls.parent)
					method.run() #TODO: or run?

			#TODO: ok, now the numbers have to add up right; either I've let untracked time creep in, or something is getting recorded wrong
			for cls in goal("run only test methods").load(["test_classes"]).classes(lambda x: x == "MostlyMethods"):
				for method in cls.methods(lambda x: x.startswith("test")):
					cls.ob.before_hook() #TODO: better/clearer/cleaner/official API for this
					method.run() #TODO: or run?
					cls.ob.after_hook()

# from bdd import Anaphora, Noun

# from bdd import Expectation, expect

# class app(Noun):
# 	def before(self):
# 		print("run before")

# 	def after(self):
# 		print("run after")

# Anaphora.idioms([app, "mindset", "goal", "action", "requirement"])

# with app("anaphora"):
# 	with mindset("developer"):
# 		with goal("configure anaphora"):
