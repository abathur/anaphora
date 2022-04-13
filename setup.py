"""Configure anaphora."""

from setuptools import setup
from anaphora.meta import Config

setup(
    name="anaphora",
    author="Travis A. Everett",
    author_email="travis.a.everett+anaphora@gmail.com",
    install_requires=["colorama", "packaging"],
    tests_require=["coverage", "flake8", "pep257"],  # tdver, , ?
    packages=["anaphora"],
    entry_points={"console_scripts": ["anaphora = anaphora.cli:main"]},
    **Config(),
)
