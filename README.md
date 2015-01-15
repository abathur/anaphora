_anaphora_
========

_anaphora_ is an expressive, flexible, agnostic testing scaffold.

## Another Python testing module, really?
My inital experience with bdd was through a JS project which used Jasmine (by way of an extension which provides a more expressive syntax).

I went looking for a Python BDD library that made the same kind of sense, but it felt like the existing libraries struggle to adapt the concepts without breaking the expressive qualities that make them worthwhile in the first place. _anaphora_ is inspired by BDD, but its flexibility doesn't mean practicing BDD is a prerequisite.

## Grammar
I realized as I was working out what grammar to use for _anaphora_, and evaluating the choices existing libraries make, that these choices can't help but make one library another either useful or useless, almost entirely based on whether the grammar it promotes fits the process of the individual or organization.

_anaphora_ encourages users to play an active role in defining the grammar they'll use. In the longer run, _anaphora_ intends to bundle the most popular grammars for easier engagement by new users. Please send a pull request if you feel like you have a grammar useful to others. See the grammars directory for an example.

## Assertions
_anaphora_ resists the urge to provide any out-of-the-box expressive assertion support (i.e., expect() or should(), etc.) because there are already projects doing a really good job of these in an array of grammars that will likely be acceptable. _anaphora_ instead aims to be compatible with these packages, and in lieu of direct support recommends:
- [ensure][ensure]
- [sure][sure]
- [expects][expects]

Other assertion modules you may find worth a look include [PyHamcrest][PyHamcrest] and [PyShould][PyShould]

[ensure]: https://github.com/kislyuk/ensure
[sure]: https://github.com/gabrielfalcao/sure
[expects]: https://github.com/jaimegildesagredo/expects
[PyHamcrest]: https://github.com/hamcrest/PyHamcrest
[PyShould]: https://github.com/drslump/pyshould
