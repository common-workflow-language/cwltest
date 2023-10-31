#!/usr/bin/env python3
import os
import pathlib
import sys
from typing import List

from setuptools import setup

SETUP_DIR = os.path.dirname(__file__)
README = os.path.join(SETUP_DIR, "README.rst")

needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)
pytest_runner: List[str] = ["pytest < 8", "pytest-runner"] if needs_pytest else []

setup(
    name="cwltest",
    description="Common Workflow Language testing framework",
    long_description=open(README).read(),
    long_description_content_type="text/x-rst",
    author="Common workflow language working group",
    author_email="common-workflow-language@googlegroups.com",
    url="https://github.com/common-workflow-language/cwltest",
    download_url="https://github.com/common-workflow-language/cwltest",
    license="Apache 2.0",
    python_requires=">=3.8,<3.13",
    use_scm_version=True,
    setup_requires=pytest_runner + ["setuptools_scm>=8.0.4,<9"],
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
    classifiers=[
        "Environment :: Console",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Typing :: Typed",
    ],
)
