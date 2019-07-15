#!/bin/bash -xe
[[ -d exported-artifacts ]] \
|| mkdir -p exported-artifacts

BUILD_DIR="$PWD/rpmbuild"

[[ -d "$BUILD_DIR/SOURCES" ]] \
|| mkdir -p "$BUILD_DIR/SOURCES"

./autogen.sh
./configure --prefix=/usr

SUFFIX=
. automation/config.sh
[ -n "${VERSION_SUFFIX}" ] && SUFFIX=".$(date -u +%Y%m%d%H%M%S).git$(git rev-parse --short HEAD)"

# build the rpms assuming the tarball is in the project's directory
rpmbuild \
    -D "_topdir $BUILD_DIR" \
    ${SUFFIX:+-D "release_suffix ${SUFFIX}"} \
    -ta *.tar.gz

# Move tarball to exported artifacts
mv *.tar.gz exported-artifacts/

# Move RPMs to exported artifacts
find "$BUILD_DIR" -iname \*rpm -exec mv "{}" exported-artifacts/ \;

