"""Configure anaphora."""

from setuptools import setup
from anaphora.meta import config

setup(
	name="anaphora",
	author="Travis A. Everett",
	author_email="travis.a.everett+anaphora@gmail.com",
	install_requires=["colorama"],
	# test_requires=[],  # tdver, pep8, pep257, pylint?
	packages=["anaphora"],
	entry_points={
		'console_scripts': [
			'anaphora = anaphora.cli:main',
		],
	},
	**config
)
