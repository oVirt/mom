#!/bin/sh
set -e

autoreconf -if

./configure
make
rm -f *.tar.gz
make rpm
