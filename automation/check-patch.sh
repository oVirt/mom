#!/bin/bash -xe
automation/build-artifacts.sh

DISTVER="$(rpm --eval "%dist"|cut -c2-3)"
PACKAGER=""
if [[ "${DISTVER}" == "el" ]]; then
    PACKAGER=yum
    cd tests
    PYTHONDONTWRITEBYTECODE=1 \
	LC_ALL=C \
	PYTHONPATH="..:./:$PYTHONPATH" \
	python2 -m coverage run --rcfile=../automation/coverage.rc testrunner.py *.py
    coverage html --rcfile=../automation/coverage.rc
    mv htmlcov ../exported-artifacts/htmlcov-py2
    cd ..
else
    PACKAGER=dnf
    cd tests
    rm -f .coverage
    PYTHONDONTWRITEBYTECODE=1 \
	LC_ALL=C \
	PYTHONPATH="..:.:$PYTHONPATH" \
	python3 -m coverage run --rcfile=../automation/coverage.rc testrunner.py *.py
    coverage3 html --rcfile=../automation/coverage.rc
    mv htmlcov ../exported-artifacts/htmlcov-py3
    cd ..
fi

${PACKAGER} --downloadonly install exported-artifacts/*noarch*.rpm
