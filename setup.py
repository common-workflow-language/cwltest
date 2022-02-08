#!/usr/bin/env python3
import os
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

install_requires = [
    "schema-salad >= 5.0.20200220195218, < 9",
    "junit-xml >= 1.8",
    "defusedxml",
]

needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)
pytest_runner = ["pytest < 8", "pytest-runner"] if needs_pytest else []

setup(
    name="cwltest",
    version="2.2",  # update the VERSION prefix in the Makefile as well 🙂
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
    package_data={"cwltest": ["py.typed"], "cwltest.tests": ["test-data/*"]},
    include_package_data=True,
    install_requires=install_requires,
    test_suite="tests",
    tests_require=["pytest<8"],
    entry_points={
        "console_scripts": [
            "cwltest=cwltest:main",
            "mock-cwl-runner=cwltest.tests.mock_cwl_runner:main",
        ]
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
        "Typing :: Typed",
    ],
)
