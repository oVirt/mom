Memory Overcommitment Manager
=============================

[![Copr build status](https://copr.fedorainfracloud.org/coprs/ovirt/ovirt-master-snapshot/package/mom/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/ovirt/ovirt-master-snapshot/package/mom/)


Welcome to the oVirt MOM source repository. This repository is hosted on
https://github.com/oVirt/mom.


INTRODUCTION
------------

MOM is a policy-driven tool that can be used to manage overcommitment on KVM
hosts.  Using a connection to the hypervisor software (either libvirt or oVirt
vdsm), MOM keeps track of active virtual machines on a host.  At a regular
collection interval, data is gathered about the host and guests. Data can come
from multiple sources (eg. the /proc interface, libvirt API calls, a client
program connected to a guest, etc). Once collected, the data is organized for
use by the policy evaluation engine.  If configured, MOM regularly evaluates a
user-supplied management policy using the collected data as input.  In response
to certain conditions, the policy may trigger reconfiguration of the system’s
overcommitment mechanisms. Currently MOM supports control of memory ballooning
and KSM but the architecture is designed to accommodate new mechanisms such as
cgroups.


QUICK INSTALLATION
------------------

If MOM is not yet packaged for your Linux distribution it can beinstalled easily
using the following sequence:

    ./autogen.sh
    ./configure
    make
    make install

To build an RPM using the included spec file you should first edit configure.ac
to set RPM version information.  You may want to set VERSION_SUFFIX to a string
that will differentiate your builds from upstream builds.  The '0.0' at the
beginning of PACKAGE_RPM_RELEASE should be changed to '1' and should be
incremented for each subsequent build of the same mom release.  Once you have
made the appropriate changes, execute the following commands to create an RPM:

    rm *.tar.gz
    ./configure
    make dist
    rpmbuild -ta mom-*.tar.gz


USAGE
-----

By default, MOM looks for its configuration file in /etc/momd.conf.  Before
starting MOM for the first time, be sure to configure it.  Sample configuration
files can be found in the doc/ sub-directory of this distribution.  The most
important configuration settings are for the Hypervisor Interface, Collectors
and Controllers.

MOM can run under two different hypervisor modes: vdsm and libvirt.  If you are
configuring a node running in an oVirt environment and are running vdsm on your
node, you would select the vdsm HypervisorInterface.  Otherwise, select libvirt
to have MOM talk directly with libvirt.

Collectors determine what data is collected from the system and how.
Controllers provide the tuning "knobs" that can be used by policies.  The exact
set of Collectors and Controllers you will need depends on the policies you want
to use.  You can find help for adjusting configuration settings by reading the
comments included in the sample configuration files.

Once configured you can start MOM.  Use your distribution's standard process if
MOM has been packaged for it.  Otherwise, start the MOM daemon (momd) yourself.

    /usr/local/sbin/momd -c <config-file> -r <policy-file>

EXAMPLES
--------

Example MOM configuration files and policies can be found in the doc/
subdirectory of this distribution.


REPORTING BUGS
--------------

Bugs can be reported in [GitHub issues](https://github.com/oVirt/mom/issues). For more
detailed instruction see the [oVirt
documentation](https://www.ovirt.org/community/report-a-bug.html) page.


CONTRIBUTING
------------

MOM is part of the oVirt family of projects.  For contact information including:
IRC, mailing lists, and bugs, see: http://www.ovirt.org/community/
