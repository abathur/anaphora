from setuptools import setup

from anaphora.meta import config

setup(
    name = "anaphora",
    install_requires = ["colorama"],
    test_requires = [], #tdver
    packages = ["anaphora"],
    entry_points = {
    'console_scripts': [
            'anaphora = anaphora.cli:main',
        ],
    },
    **config
)
