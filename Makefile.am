# Copyright (C) 2012 Royce Lv, IBM Corporation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

include $(top_srcdir)/build-aux/Makefile.subs

# This is an *exception*, we ship also mom.spec and setup.py so it's possible to build
# the rpm from the tarball.
EXTRA_DIST = \
	build-aux/pkg-version \
	mom.spec \
	mom.spec.in \
	setup.py \
	setup.py.in

CLEANFILES = \
	setup.py \
	mom.spec \
	$(DIST_ARCHIVES)

all-local: \
	mom.spec\
	setup.py

.PHONY: srpm rpm

sdist:
	python setup.py sdist -d $(top_builddir)
srpm: sdist
	rpmbuild -ts $(if $(BUILDID),--define="extra_release .$(BUILDID)") $(DIST_ARCHIVES)
rpm: sdist
	rpmbuild -ta $(if $(BUILDID),--define="extra_release .$(BUILDID)") $(DIST_ARCHIVES)
dist-hook: gen-VERSION gen-ChangeLog
.PHONY: gen-VERSION gen-ChangeLog

# Generate the ChangeLog file and insert it into the directory
# we're about to use to create a tarball.
gen-ChangeLog:
	if test -d .git; then					\
	  $(top_srcdir)/build-aux/gitlog-to-changelog		\
	    > $(distdir)/cl-t;					\
	  rm -f $(distdir)/ChangeLog;				\
	  mv $(distdir)/cl-t $(distdir)/ChangeLog;		\
	fi

gen-VERSION:
	if test -d .git; then					\
	  $(top_srcdir)/build-aux/pkg-version --full		\
	    > $(distdir)/ve-t;					\
	  rm -f $(distdir)/VERSION;				\
	  mv $(distdir)/ve-t $(distdir)/VERSION;		\
	fi
