from anaphora import Anaphora

assert Anaphora.children == Anaphora.nouns == [], "Anaphora object should have no history, yet."

Anaphora.grammar(["boot"])

assert Anaphora.nouns == [boot], "Anaphora object should have exactly one noun."
Anaphora.grammar(["strap"])

# boot should only test major structural parts of the module that
# must work for the rest of the tests to function.
with boot("make sure we can configure Anaphora") as bootstrap:

	#implied test of nesting Nouns
	with strap("make sure we can use existing idioms"):
		assert isinstance(bootstrap.children[0], strap) #not sure offhand

	with strap("make sure we can create fresh/local nouns"):
		bootstrap.grammar(["foo", "bar"])
		assert foo
		assert bar
		assert bootstrap.nouns == [foo, bar]

		with foo("use them to capture an error...") as child:
			#intentional error
			assert len(child.stats.exceptions) == 1, "We shouldn't have any errors yet"

		with bar("continue execution") as child:
			assert child.parent.stats.failures == 1, "We should already have exactly one error."

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
				assert this.stats.checkpoint is not None, "node has no tracked time checkpoint."

			def after(node):
				import datetime
				assert node.stats.runtime[node.DURING] > datetime.timedelta(), "node has no tracked runtime."

			with requirement("runtime has accumulated", after=after):
				import uuid
				for x in range(1000):
					uuid.uuid4()


		with goal("count successes/failures") as child:
			assert child.stats.successes == 0, "We should have no local successes."
			assert Anaphora.stats.failures == 1, "Previous local failure not recorded."
			assert Anaphora.stats.successes == 12, "Previous global success not recorded."

		#TODO this is awkward now, since report is outside of the core
		# with goal("and print a status report"):
		# 	assert Anaphora.report() == Anaphora.report()

	with need("queryable coverage statistics"):
		with goal("coverage statistics are computed as tests run"):
			with requirement("anaphora's files only get included "
				"when they are being intentionally tested"):
				...
			with requirement("stubbeh"):
				...
		with goal("coverage statistics may be queried after tests run"):
			...

	# implicit test of the batch randomizer
	with need("integrate other types of tests with anaphora run"):
		with goal("include additional files in the test run"):
			with goal("register list of files to include"):
				with requirement("correct files are added"):
					...
				with requirement("incorrect files squeak"):
					...
			with goal("run tests in additional files"):
				...
				with requirement("tests are run in random order"):
					...
		with goal("include additional directories in the test run"):
			with goal("directories parsed into lists of registered files"):
				...
		with goal("include additional functions in the test run"):
			with goal("register list of functions to run"):
				with requirement("correct functions are added"):
					...
				with requirement("incorrect functions squeak"):
					...
		with goal("include additional classes in the test run"):
			with goal("classes parsed into lists of registered functions"):
				with requirement("correct classes are added"):
					...
				with requirement("incorrect classes squeak"):
					...
			#do these need to be re-run for other types? is there a notion of a mix-in test? do these need to just get used first AS a class and recycled within the other types? Odd idea...
			with goal("run tests in additional classes"):
				with requirement("function-matching regex is respected"):
					...
				with goal("functions may be run in random order"):
					...
				with goal("functions may be run in defined order"):
					...
				with goal("functions may be run in sort order determined by closure"):
					...

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
