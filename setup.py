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

install_requires = ["schema-salad >= 5.0.20200220195218", "junit-xml >= 1.8"]

needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)
pytest_runner = ["pytest < 6", "pytest-runner < 5"] if needs_pytest else []

setup(
    name="cwltest",
    version="2.0",
    description="Common workflow language testing framework",
    long_description=open(README).read(),
    long_description_content_type="text/x-rst",
    author="Common workflow language working group",
    author_email="common-workflow-language@googlegroups.com",
    url="https://github.com/common-workflow-language/cwltest",
    download_url="https://github.com/common-workflow-language/cwltest",
    license="Apache 2.0",
    packages=["cwltest", "cwltest.tests"],
    package_data={"cwltest.tests": ["test-data/*"]},
    include_package_data=True,
    install_requires=install_requires,
    test_suite="tests",
    setup_requires=[] + pytest_runner,
    tests_require=["pytest<5"],
    entry_points={
        "console_scripts": [
            "cwltest=cwltest:main",
            "mock-cwl-runner=cwltest.tests.mock_cwl_runner:main",
        ]
    },
    zip_safe=True,
    cmdclass={"egg_info": tagger},
    python_requires=">=3.5, <4",
)
