#!/bin/bash

set -e
set -x

export LC_ALL=C

package=cwltest
module=cwltest
slug=${TRAVIS_PULL_REQUEST_SLUG:=common-workflow-language/${module}}
repo=https://github.com/${slug}.git
run_tests="bin/py.test --pyargs ${module}"
pipver=20.3b1 # minimum required version of pip for Python 3.9
setuptoolsver=41.1.0 # required for Python 3.9

rm -Rf "testenv${PYVER}_"? || /bin/true

export HEAD=${TRAVIS_PULL_REQUEST_SHA:-$(git rev-parse HEAD)}

if [ "${RELEASE_SKIP}" != "head" ]
then
	python3 -m venv testenv1
	# First we test the head
	# shellcheck source=/dev/null
	source testenv1/bin/activate
	rm -Rf testenv1/local
	rm -f testenv1/lib/python-wheels/setuptools* \
		&& pip install --force-reinstall -U pip==${pipver} \
		&& pip install setuptools==${setuptoolsver} wheel
	make install-dependencies
	make test
	pip uninstall -y ${package} || true; pip uninstall -y ${package} \
		|| true; make install
	mkdir testenv1/not-${module}
	# if there is a subdir named '${module}' py.test will execute tests
	# there instead of the installed module's tests
	pushd testenv1/not-${module}
	# shellcheck disable=SC2086
	../${run_tests}; popd
fi

python3 -m venv testenv2
python3 -m venv testenv3
python3 -m venv testenv4
python3 -m venv testenv5
rm -Rf testenv[2345]/local

# Secondly we test via pip

pushd testenv2
# shellcheck source=/dev/null
source bin/activate
rm -f lib/python-wheels/setuptools* \
	&& pip install --force-reinstall -U pip==${pipver} \
        && pip install setuptools==${setuptoolsver} wheel
# The following can fail if you haven't pushed your commits to ${repo}
pip install -e "git+${repo}@${HEAD}#egg=${package}"
pushd src/${package}
make install-dependencies
make dist
make test
cp dist/${package}*tar.gz ../../../testenv3/
cp dist/${module}*whl ../../../testenv4/
pip uninstall -y ${package} || true; pip uninstall -y ${package} || true; make install
popd # ../.. no subdir named ${proj} here, safe for py.testing the installed module
# shellcheck disable=SC2086
${run_tests}
popd

# Is the source distribution in testenv2 complete enough to build
# another functional distribution?

pushd testenv3/
# shellcheck source=/dev/null
source bin/activate
rm -f lib/python-wheels/setuptools* \
	&& pip install --force-reinstall -U pip==${pipver} \
        && pip install setuptools==${setuptoolsver} wheel
pip install ${package}*tar.gz
pip install pytest\<5
mkdir out
tar --extract --directory=out -z -f ${package}*.tar.gz
pushd out/${package}*
make dist
make test
pip uninstall -y ${package} || true; pip uninstall -y ${package} || true; make install
mkdir ../not-${module}
pushd ../not-${module}
# shellcheck disable=SC2086
../../${run_tests}; popd
popd
popd

# Is the wheel in testenv2 installable and will it pass the tests

pushd testenv4/
# shellcheck source=/dev/null
source bin/activate
rm -f lib/python-wheels/setuptools* \
	&& pip install --force-reinstall -U pip==${pipver} \
        && pip install setuptools==${setuptoolsver} wheel
pip install ${module}*.whl
pip install pytest\<5
mkdir not-${module}
pushd not-${module}
# shellcheck disable=SC2086
../${run_tests}; popd
popd
