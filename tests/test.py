from anaphora import Noun
import sys

ANAPHORA = Noun("AnaphoraSingleton")

assert (
    ANAPHORA.exceptions == ANAPHORA.nouns == []
), "Anaphora object should have no history, yet."

ANAPHORA.grammar(["boot"])

assert ANAPHORA.nouns == [boot], "Anaphora object should have exactly one noun."
ANAPHORA.grammar(["strap"])

# boot should only test major structural parts of the module that
# must work for the rest of the tests to function.
with boot("make sure we can configure Anaphora") as bootstrap:
    with strap("make sure we can create fresh/local nouns"):
        bootstrap.grammar(["foo", "bar"])
        assert foo
        assert bar
        assert bootstrap.nouns == [foo, bar]

        with foo("use them to capture an error...") as child1:
            child1.ignore()
            # we have to preserve this to introspect the failure
            bootstrap.child1 = child1
            # intentional error
            assert len(child1.exceptions) == 1, "We shouldn't have any errors yet"

        with bar("and continue execution"):
            assert bootstrap.child1.succeeded == 0, "We should have a recorded failure."

    with strap(
        "local grammar additions are cleaned up when they exit scope"
    ) as strapping:
        assert "foo" not in locals(), "Local 'foo' wasn't cleaned up."
        assert "bar" not in locals(), "Local 'bar' wasn't cleaned up."

    with strap("nodes should also get cleaned up when they exit scope"):
        assert "strapping" not in locals(), "strapping wasn't cleaned up."

del boot
del strap
ANAPHORA.nouns = []
ANAPHORA.grammar(["app"])
with app("Anaphora").grammar(["need", "goal", "requirement"]):
    with need("customize tests with before/after hooks"):
        i = 0
        ahyuk = "ahyuk"

        def test_hook(node):
            global i
            i += 10

        def terminal_hook(node):
            print(ahyuk)
            raise IOError

        with goal("register successful before hook", before=test_hook) as this:
            assert len(this.hooks[this.hooks.BEFORE]) == 1, "No before hook registered."
            with requirement("before hook executes successfully"):
                assert i == 10, "Before hook failed to run successfully."

        with goal("register successful after hook", after=test_hook) as this:
            assert len(this.hooks[this.hooks.AFTER]) == 1, "No after hook registered."

        with requirement("all hooks execute successfully"):
            # we're testing that both the before and after hook executed.
            assert i == 20, "Hooks failed to run successfully."

        with goal("hook failures are properly tracked") as tracker:
            with requirement(
                "bad before_hook fails properly", before=terminal_hook
            ) as this:
                this.ignore()
                tracker.before = this

            with requirement("before_hook failure is tracked"):
                assert len(tracker.before.exceptions), "Before hook failure not tracked"

                with requirement("exception captures output"):
                    assert (
                        tracker.before.exceptions[0].output == ahyuk
                    ), "Exception didn't capture output"

            with requirement(
                "bad after_hook fails properly", after=terminal_hook
            ) as this:
                this.ignore()
                tracker.after = this

            with requirement("after_hook failure is tracked"):
                assert len(tracker.after.exceptions), "After hook failure not tracked"

    with need("queryable testing statistics") as parent:
        with goal("track runtime"):
            with requirement("checkpoint has been set") as funtime:
                parent.funtime = funtime  # save for next test
                assert (
                    funtime.runtime.check().total_seconds() > 0
                ), "node has no tracked time checkpoint."

            with requirement("runtime accumulated"):
                import datetime

                assert (
                    parent.funtime.runtime["during"].total_seconds() > 0
                ), "node has no tracked runtime."

        with goal("success is tracked"):
            assert parent.funtime.succeeded == 1, "Success should have been tracked."

        with goal("statistics are queryable"):
            assert (
                parent.db.execute(
                    "SELECT succeeded FROM nodes WHERE id=?;", (parent.funtime.id,)
                ).fetchone()[0]
                == 1
            )

    with need("queryable coverage statistics") as bleh:
        bleh.skip()  # coverage integration delayed
        with goal("coverage statistics are computed as tests run"):
            with requirement(
                "anaphora's files only get included "
                "when they are being intentionally tested"
            ):
                ...
            with requirement("stubbeh"):
                ...
        with goal("coverage statistics may be queried after tests run"):
            ...  # this is an absurd thing to test at this point, no?

    with need("integrate other types of tests with anaphora run"):
        with goal("run test functions from additional modules"):

            wert = 9
            for func in goal("run all functions").load(["tests.test3"]).functions():
                wert = func.run(wert)
            assert wert == 5, "Imported functions didn't run successfully."

            for func in (
                goal("run only functions matching a predicate")
                .load(["tests.test3"])
                .functions(lambda x: x == "test2")
            ):
                wert = func.run(wert)
            assert wert == 10, "Imported function didn't run successfully."

        with goal("run test methods on additional classes"):
            for method in (
                requirement("chain selectors to run all " + "matching class methods")
                .load(["tests.test_classes"])
                .classes(lambda x: x == "JustMethods")
                .methods()
            ):
                method.run()

            for cls in (
                requirement("or run the same methods class by class")
                .load(["tests.test_classes"])
                .classes(lambda x: x == "JustMethods")
            ):
                for method in cls.methods():
                    method.run()

            for cls in (
                requirement("run only test methods")
                .load(["tests.test_classes"])
                .classes(lambda x: x == "MostlyMethods")
            ):

                cls.test.before_class_hook()
                for method in cls.methods(lambda x: x.startswith("test")):
                    cls.test.before_method_hook()
                    method.run()
                    cls.test.after_method_hook()

                cls.test.after_class_hook()

        for garol in requirement("run external test module").load(["tests.external"]):
            assert garol.test.i_swear_i_am_the_external_tests() == True

        for garol in requirement("run another executable as a test").commands(
            ["flake8 anaphora"]  # --ignore=W191
        ):
            garol.run()

        with goal("run earmarks") as marker:
            with requirement("only run tests that pass a version check") as lint:
                linted = []
                # a single if/else would be more efficient
                # but would make this test pointless
                if lint.earmark(">=1"):
                    # linted.append(lint.command("pylint anaphora"))
                    linted.append(lint.command("pep257 anaphora"))

                if lint.earmark("<1"):
                    # linted.append(
                    #     lint.command("pylint anaphora --disable=missing-docstring,")
                    # )
                    linted.append(lint.command("pep257 anaphora", warn=True))

                assert len(linted), "No earmarks were run."
                assert len(linted) < 2, "Earmark version constraint violated."
