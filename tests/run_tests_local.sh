#!/bin/sh
PYTHONDONTWRITEBYTECODE=1 \
LC_ALL=C \
PYTHONPATH="..:$PYTHONPATH" \
/usr/bin/python ../tests/testrunner.py $@
