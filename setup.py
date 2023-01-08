#!/usr/bin/env python3
import os
import pathlib
import sys

import setuptools.command.egg_info as egg_info_cmd
from setuptools import setup

SETUP_DIR = os.path.dirname(__file__)
README = os.path.join(SETUP_DIR, "README.rst")

try:
    import gittaggers

    tagger = gittaggers.EggInfoFromGit
except ImportError:
    tagger = egg_info_cmd.egg_info

needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)
pytest_runner = ["pytest < 8", "pytest-runner"] if needs_pytest else []

setup(
    name="cwltest",
    version="2.3",  # update the VERSION prefix in the Makefile as well 🙂
    description="Common Workflow Language testing framework",
    long_description=open(README).read(),
    long_description_content_type="text/x-rst",
    author="Common workflow language working group",
    author_email="common-workflow-language@googlegroups.com",
    url="https://github.com/common-workflow-language/cwltest",
    download_url="https://github.com/common-workflow-language/cwltest",
    license="Apache 2.0",
    python_requires=">=3.6, <4",
    setup_requires=[] + pytest_runner,
    packages=["cwltest", "cwltest.tests"],
    package_dir={"cwltest.tests": "tests"},
    package_data={"cwltest": ["py.typed"], "tests": ["test-data/*"]},
    include_package_data=True,
    install_requires=open(
        os.path.join(pathlib.Path(__file__).parent, "requirements.txt")
    )
    .read()
    .splitlines(),
    test_suite="tests",
    tests_require=open(
        os.path.join(pathlib.Path(__file__).parent, "test-requirements.txt")
    )
    .read()
    .splitlines(),
    extras_require={"pytest-plugin": ["pytest"]},
    entry_points={
        "console_scripts": [
            "cwltest=cwltest.main:main",
        ],
        "pytest11": [
            "cwl = cwltest.plugin [pytest-plugin]",
        ],
    },
    zip_safe=True,
    cmdclass={"egg_info": tagger},
    classifiers=[
        "Environment :: Console",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Typing :: Typed",
    ],
)
