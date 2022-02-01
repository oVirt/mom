#!/bin/bash -xe
automation/build-artifacts.sh

cd tests
rm -f .coverage
PYTHONDONTWRITEBYTECODE=1 \
    LC_ALL=C \
    PYTHONPATH="..:.:$PYTHONPATH" \
    python3 -m coverage run --rcfile=../automation/coverage.rc testrunner.py ./*.py
python3 -m coverage html --rcfile=../automation/coverage.rc
mv htmlcov "../${EXPORT_DIR}/htmlcov-py3"
cd ..

dnf --downloadonly install -y "${EXPORT_DIR}"/*noarch*.rpm
