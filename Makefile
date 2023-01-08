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

# make format to fix most python formatting errors
# make pylint to check Python code for enhanced compliance including naming
#  and documentation
# make coverage-report to check coverage of the python scripts by the tests

MODULE=cwltest
PACKAGE=cwltest

# `SHELL=bash` doesn't work for some, so don't use BASH-isms like
# `[[` conditional expressions.
PYSOURCES=$(wildcard ${MODULE}/**.py tests/*.py) setup.py
DEVPKGS=-rdev-requirements.txt -rtest-requirements.txt -rmypy-requirements.txt
DEBDEVPKGS=pep8 python-autopep8 pylint python-coverage pydocstyle sloccount \
	   python-flake8 python-mock shellcheck
VERSION=2.3.$(shell TZ=UTC git log --first-parent --max-count=1 \
	--format=format:%cd --date=format-local:%Y%m%d%H%M%S)

## all                    : default task (install in dev mode)
all: dev

## help                   : print this help message and exit
help: Makefile
	@sed -n 's/^##//p' $<

## cleanup                : shortcut for "make sort_imports format flake8 diff_pydocstyle_report"
cleanup: sort_imports format flake8 diff_pydocstyle_report

## install-dep            : install most of the development dependencies via pip
install-dep: install-dependencies

install-dependencies: FORCE
	pip install --upgrade $(DEVPKGS)
	pip install -r requirements.txt

## install-deb-dep        : install most of the dev dependencies via apt-get
install-deb-dep:
	sudo apt-get install $(DEBDEVPKGS)

## install                : install the cwltest package and cwltest script
install: FORCE
	pip install .

## dev                    : install the cwltest package in dev mode
dev: install-dep
	pip install -U pip setuptools wheel
	pip install -e .

## dist                   : create a module package for distribution
dist: dist/${MODULE}-$(VERSION).tar.gz

dist/${MODULE}-$(VERSION).tar.gz: $(SOURCES)
	python -m build

## docs                   : make the docs
docs: FORCE
	cd docs && $(MAKE) html

## clean                  : clean up all temporary / machine-generated files
clean: FORCE
	rm -f ${MODILE}/*.pyc tests/*.pyc
	python setup.py clean --all || true
	rm -Rf .coverage\.* .coverage
	rm -f diff-cover.html

# Linting and code style related targets
## sort_import            : sorting imports using isort: https://github.com/timothycrosley/isort
sort_imports: $(PYSOURCES) mypy-stubs
	isort $^

remove_unused_imports: $(filter-out schema_salad/metaschema.py,$(PYSOURCES))
	autoflake --in-place --remove-all-unused-imports $^

pep257: pydocstyle
## pydocstyle             : check Python docstring style
pydocstyle: $(PYSOURCES)
	pydocstyle --add-ignore=D100,D101,D102,D103 $^ || true

pydocstyle_report.txt: $(PYSOURCES)
	pydocstyle setup.py $^ > $@ 2>&1 || true

## diff_pydocstyle_report : check Python docstring style for changed files only
diff_pydocstyle_report: pydocstyle_report.txt
	diff-quality --compare-branch=main --violations=pydocstyle --fail-under=100 $^

## codespell              : check for common misspellings
codespell:
	codespell -w $(shell git ls-files | grep -v mypy-stubs | grep -v gitignore)

## format                 : check/fix all code indentation and formatting (runs black)
format: $(PYSOURCES) mypy-stubs
	black $^

format-check: $(PYSOURCES) mypy-stubs
	black --diff --check $^

## pylint                 : run static code analysis on Python code
pylint: $(PYSOURCES)
	pylint --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" \
                $^ -j0|| true

pylint_report.txt: $(PYSOURCES)
	pylint --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" \
		$^ -j0> $@ || true

diff_pylint_report: pylint_report.txt
	diff-quality --compare-branch=main --violations=pylint pylint_report.txt

.coverage: $(PYSOURCES)
	COV_CORE_SOURCE=cwltest COV_CORE_CONFIG=.coveragerc COV_CORE_DATAFILE=.coverage \
		python -m pytest --cov --cov-append --cov-report=
	# https://pytest-cov.readthedocs.io/en/latest/plugins.html#plugin-coverage

coverage.xml: .coverage
	coverage xml

coverage.html: htmlcov/index.html

htmlcov/index.html: .coverage
	coverage html
	@echo Test coverage of the Python code is now in htmlcov/index.html

coverage-report: .coverage
	coverage report

diff-cover: coverage.xml
	diff-cover --compare-branch=main $^

diff-cover.html: coverage.xml
	diff-cover --compare-branch=main $^ --html-report $@

## test                   : run the cwltest test suite
test: $(PYSOURCES)
	python -m pytest -rs ${PYTEST_EXTRA}

## testcov                : run the cwltest test suite and collect coverage
testcov: $(PYSOURCES)
	python setup.py test --addopts "--cov" ${PYTEST_EXTRA}

sloccount.sc: $(PYSOURCES) Makefile
	sloccount --duplicates --wide --details $^ > $@

## sloccount              : count lines of code
sloccount: $(PYSOURCES) Makefile
	sloccount $^

list-author-emails:
	@echo 'name, E-Mail Address'
	@git log --format='%aN,%aE' | sort -u | grep -v 'root'

mypy3: mypy
mypy: $(filter-out setup.py gittagger.py,$(PYSOURCES))
	MYPYPATH=$$MYPYPATH:mypy-stubs mypy $^

mypy_3.6: $(filter-out setup.py gittagger.py,$(PYSOURCES))
	MYPYPATH=$$MYPYPATH:mypy-stubs mypy --python-version 3.6 $^

pyupgrade: $(filter-out schema_salad/metaschema.py,$(PYSOURCES))
	pyupgrade --exit-zero-even-if-changed --py36-plus $^

release-test: FORCE
	git diff-index --quiet HEAD -- || ( echo You have uncommitted changes, please commit them and try again; false )
	./release-test.sh

release: release-test
	. testenv2/bin/activate && \
		pip install build && \
		python -m build testenv2/src/${PACKAGE} && \
		pip install twine && \
		twine upload testenv2/src/${PACKAGE}/dist/* && \
		git tag ${VERSION} && git push --tags

flake8: $(PYSOURCES)
	flake8 $^

FORCE:

# Use this to print the value of a Makefile variable
# Example `make print-VERSION`
# From https://www.cmcrossroads.com/article/printing-value-makefile-variable
print-%  : ; @echo $* = $($*)
