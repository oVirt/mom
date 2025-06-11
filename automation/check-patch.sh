#!/bin/bash -xe
automation/build-artifacts.sh

rm -f .coverage htmlcov
tox --parallel auto

dnf --downloadonly install -y "${EXPORT_DIR}"/*noarch*.rpm
