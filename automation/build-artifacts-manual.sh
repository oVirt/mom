#!/bin/bash -xe
[[ -d exported-artifacts ]] \
|| mkdir -p exported-artifacts

[[ -d rpmbuild/SOURCES ]] \
|| mkdir -p rpmbuild/SOURCES

./autogen.sh
./configure --prefix=/usr

# build the rpms assuming the tarball is in the project's directory
rpmbuild -ta *.tar.gz

# Move tarball to exported artifacts
mv *.tar.gz exported-artifacts/

# Move RPMs to exported artifacts
find rpmbuild -iname \*rpm -exec mv "{}" exported-artifacts/ \;

