# This file is part of cwltest,
# https://github.com/common-workflow-language/cwltest/, and is
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Contact: common-workflow-language@googlegroups.com

# make pycodestyle to check for basic Python code compliance
# make autopep8 to fix most pep8 errors
# make pylint to check Python code for enhanced compliance including naming
#  and documentation
# make coverage-report to check coverage of the python scripts by the tests

MODULE=cwltest

# `SHELL=bash` doesn't work for some, so don't use BASH-isms like
# `[[` conditional expressions.
PYSOURCES=$(wildcard ${MODULE}/**.py tests/*.py) setup.py
DEVPKGS=pycodestyle diff_cover pylint coverage pydocstyle flake8 \
	pytest pytest-xdist isort
DEBDEVPKGS=pep8 python-autopep8 pylint python-coverage pydocstyle sloccount \
	   python-flake8 python-mock shellcheck
VERSION=2.0.$(shell TZ=UTC git log --first-parent --max-count=1 \
	--format=format:%cd --date=format-local:%Y%m%d%H%M%S)
mkfile_dir := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

## all         : default task
all: FORCE
	pip install -e .

## help        : print this help message and exit
help: Makefile
	@sed -n 's/^##//p' $<

install-dependencies: install-dep
## install-dep : install most of the development dependencies via pip
install-dep:
	pip install --upgrade $(DEVPKGS)
	pip install -r requirements.txt

## install-deb-dep: install most of the dev dependencies via apt-get
install-deb-dep:
	sudo apt-get install $(DEBDEVPKGS)

## install     : install the ${MODULE} module and schema-salad-tool
install: FORCE
	pip install .

## dist        : create a module package for distribution
dist: dist/${MODULE}-$(VERSION).tar.gz

dist/${MODULE}-$(VERSION).tar.gz: $(SOURCES)
	./setup.py sdist bdist_wheel

## clean       : clean up all temporary / machine-generated files
clean: FORCE
	rm -f ${MODILE}/*.pyc tests/*.pyc
	./setup.py clean --all || true
	rm -Rf .coverage
	rm -f diff-cover.html

# Linting and code style related targets
## sorting imports using isort: https://github.com/timothycrosley/isort
sort_imports:
	isort ${MODULE}/*.py tests/*.py setup.py

pep257: pydocstyle
## pydocstyle      : check Python code style
pydocstyle: $(PYSOURCES)
	pydocstyle --add-ignore=D100,D101,D102,D103 $^ || true

pydocstyle_report.txt: $(PYSOURCES)
	pydocstyle setup.py $^ > $@ 2>&1 || true

diff_pydocstyle_report: pydocstyle_report.txt
	diff-quality --violations=pycodestyle --fail-under=100 $^

## format      : check/fix all code indentation and formatting (runs black)
format:
	black --exclude cwltool/schemas setup.py cwltest

## pylint      : run static code analysis on Python code
pylint: $(PYSOURCES)
	pylint --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" \
                $^ -j0|| true

pylint_report.txt: ${PYSOURCES}
	pylint --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" \
		$^ -j0> $@ || true

diff_pylint_report: pylint_report.txt
	diff-quality --violations=pylint pylint_report.txt

.coverage: $(PYSOURCES) all
	coverage run ./setup.py test

coverage.xml: .coverage
	python-coverage xml

coverage.html: htmlcov/index.html

htmlcov/index.html: .coverage
	python-coverage html
	@echo Test coverage of the Python code is now in htmlcov/index.html

coverage-report: .coverage
	python-coverage report

diff-cover: coverage-gcovr.xml coverage.xml
	diff-cover coverage-gcovr.xml coverage.xml

diff-cover.html: coverage-gcovr.xml coverage.xml
	diff-cover coverage-gcovr.xml coverage.xml \
		--html-report diff-cover.html

## test        : run the ${MODULE} test suite
test: all
	./setup.py test

sloccount.sc: ${PYSOURCES} Makefile
	sloccount --duplicates --wide --details $^ > $@

## sloccount   : count lines of code
sloccount: ${PYSOURCES} Makefile
	sloccount $^

list-author-emails:
	@echo 'name, E-Mail Address'
	@git log --format='%aN,%aE' | sort -u | grep -v 'root'

mypy3: mypy
mypy: ${PYSOURCES}
	if ! test -f $(shell python3 -c 'import ruamel.yaml; import os.path; print(os.path.dirname(ruamel.yaml.__file__))')/py.typed ; \
	then \
		rm -Rf typeshed/2and3/ruamel/yaml ; \
		ln -s $(shell python3 -c 'import ruamel.yaml; import os.path; print(os.path.dirname(ruamel.yaml.__file__))') \
			typeshed/2and3/ruamel/ ; \
	fi  # if minimally required ruamel.yaml version is 0.15.99 or greater, than the above can be removed
	MYPYPATH=$$MYPYPATH:typeshed/3:typeshed/2and3 mypy --disallow-untyped-calls \
		 --warn-redundant-casts \
		 ${MODULE}

release-test: FORCE
	git diff-index --quiet HEAD -- || ( echo You have uncommited changes, please commit them and try again; false )
	./release-test.sh

release: FORCE
	PYVER=3 ./release-test.sh
	. testenv3_2/bin/activate && \
		testenv3_2/src/${MODULE}/setup.py sdist bdist_wheel
	. testenv3_2/bin/activate && \
		pip install twine && \
		twine upload testenv3_2/src/${MODULE}/dist/*whl && \
		git tag ${VERSION} && git push --tags

FORCE:

# Use this to print the value of a Makefile variable
# Example `make print-VERSION`
# From https://www.cmcrossroads.com/article/printing-value-makefile-variable
print-%  : ; @echo $* = $($*)
