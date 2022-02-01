#!/bin/bash -xe
[[ -d "${EXPORT_DIR}" ]] \
|| mkdir -p "${EXPORT_DIR}"

# mock runner is not setting up the system correctly
# https://issues.redhat.com/browse/CPDEVOPS-242
readarray -t pkgs < automation/build-artifacts.packages
dnf install -y "${pkgs[@]}"


BUILD_DIR="$PWD/rpmbuild"

[[ -d "$BUILD_DIR/SOURCES" ]] \
|| mkdir -p "$BUILD_DIR/SOURCES"

./autogen.sh
./configure --prefix=/usr
make dist

SUFFIX=
# shellcheck source=config.sh
SUFFIX=".$(date -u +%Y%m%d%H%M%S).git$(git rev-parse --short HEAD)"

rpmbuild \
    -D "_topdir $BUILD_DIR" \
    ${SUFFIX:+-D "release_suffix ${SUFFIX}"} \
    -ta ./*.tar.gz

# Move tarball to exported artifacts
mv ./*.tar.gz "${EXPORT_DIR}/"

# Move RPMs to exported artifacts
find "$BUILD_DIR" -iname \*rpm -exec mv "{}" "${EXPORT_DIR}/" \;
