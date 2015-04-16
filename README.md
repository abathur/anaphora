## _anaphora_: An agnostic, flexibly-expressive scaffold for structured testing

_anaphora_ is for adding structure and semantics to your test runs. It doesn't come with strong opinions about what grammar, meaning, or kind of tests will be right for your teams and projects. Instead, _anaphora_ lets you define these as you go.

This agnosticism extends to what a test should look like. While the canonical test is written into the _anaphora_ file (with plain assertions or any assertion library you prefer), there's also a simple API for running tests elsewhere. This makes it easy to select, filter (via a predicate callable), and run:
* all functions in a given module
* only functions in a module that start with "test"
* all methods on all classes
* only methods that start with "test" on classes that end with "Test"
* other command-line executables (like linters, tests for other languages in your project, etc.)

Taken together, these features mean an _anaphora_ run could integrate linters with behavior, regression, and unit tests.

## Requirements
_anaphora_ requires Python 3 to run, and pip for Python 3 to install additional dependencies.

## Getting started
_anaphora_ is still nascent enough that it isn't quite released and as such has no version. The 0.0.1 release will come as soon as _anaphora_ has been given a good workout, but a quick look in tests/* should be enough to show you how to put it through the paces yourself.

## Documentation
Coming soon.

## Assertions
Even though you can use whatever assertions you like with _anaphora_, expressive assertions are probably the best fit. If you don't already have a favorite, these are a good place to start looking:
- [ensure][ensure]
- [sure][sure]
- [expects][expects]

Others you may find worth a look include: [PyHamcrest][PyHamcrest] and [PyShould][PyShould]

[ensure]: https://github.com/kislyuk/ensure
[sure]: https://github.com/gabrielfalcao/sure
[expects]: https://github.com/jaimegildesagredo/expects
[PyHamcrest]: https://github.com/hamcrest/PyHamcrest
[PyShould]: https://github.com/drslump/pyshould
