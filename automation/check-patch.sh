#!/bin/bash -xe
automation/build-artifacts.sh

DISTVER="$(rpm --eval "%dist"|cut -c2-3)"
PACKAGER=""
if [[ "${DISTVER}" == "el" ]]; then
    PACKAGER=yum
else
    PACKAGER=dnf
fi

${PACKAGER} --downloadonly install exported-artifacts/*noarch*.rpm
