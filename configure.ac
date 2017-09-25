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

AC_PREREQ(2.60)

define([VERSION_MAJOR], [0])
define([VERSION_MINOR], [5])
define([VERSION_FIX], [11])
define([VERSION_NUMBER], VERSION_MAJOR[.]VERSION_MINOR[.]VERSION_FIX)
define([VERSION_SUFFIX], [_master])

AC_INIT([mom], VERSION_NUMBER[]VERSION_SUFFIX, [mom-devel@googlegroups.com])
PACKAGE_RPM_VERSION="VERSION_NUMBER"
PACKAGE_RPM_RELEASE="0.0.$(echo VERSION_SUFFIX | sed 's/^_//')"
AC_SUBST([PACKAGE_RPM_VERSION])
AC_SUBST([PACKAGE_RPM_RELEASE])

AC_CONFIG_AUX_DIR([.])
AC_CONFIG_SRCDIR([mom/GuestManager.py])
AC_CONFIG_MACRO_DIR([m4])
AM_INIT_AUTOMAKE

AC_ARG_ENABLE(
	[python-syntax-check],
	[AS_HELP_STRING([--disable-python-syntax-check], [disable python syntax check @<:@default=enabled@:>@])],
	,
	[enable_python_syntax_check="no"]
)

AC_PROG_INSTALL

AM_PATH_PYTHON([2.6],,[AC_MSG_ERROR([Cannot find python])])
case "${PYTHON_VERSION}" in
	2.*);;
	*) AC_MSG_ERROR([python 2.6 is required])
esac

AC_ARG_VAR([PYFLAKES], [path to pyflakes utility])
AC_CHECK_PROGS([PYFLAKES], [pyflakes])
AC_ARG_VAR([PEP8], [path to pep8 utility])
AC_CHECK_PROGS([PEP8], [pep8])

AX_PYTHON_MODULE([nose])

AM_CONDITIONAL([PYTHON_SYNTAX_CHECK], [test "${enable_python_syntax_check}" = "yes"])

AC_CONFIG_FILES([
	mom.spec
	Makefile
	contrib/Makefile
	doc/Makefile
	mom/Makefile
	mom/Collectors/Makefile
	mom/Controllers/Makefile
	mom/debug/Makefile
	mom/HypervisorInterfaces/Makefile
	mom/Policy/Makefile
	tests/Makefile
])
AC_CONFIG_FILES(
	[tests/run_tests_local.sh],
	[chmod a+x tests/run_tests_local.sh],
)
AC_OUTPUT
