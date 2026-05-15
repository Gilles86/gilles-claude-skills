"""Minimal setup.py for a cognitive-neuroscience fMRI project.

Conda handles all heavy deps via create_env/environment_*.yml.
This file just makes `pip install -e .` work for editable installs.
"""
from setuptools import setup, find_packages

setup(
    name='<project>',
    version='0.1.0',
    packages=find_packages(),
    package_data={
        '<project>': ['data/subjects.yml'],
    },
    include_package_data=True,
    python_requires='>=3.10',
    install_requires=[],  # all deps in conda env
)
