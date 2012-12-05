#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_INIT([mom],
        [m4_esyscmd([build-aux/pkg-version --version])],
        [mom-devel@googlegroups.com])

AC_CONFIG_AUX_DIR([build-aux])

# Checks for package release
AC_SUBST([PACKAGE_RELEASE],
         [m4_esyscmd([build-aux/pkg-version --release])])

AS_IF([test "x$PACKAGE_VERSION" = x],
      AC_MSG_ERROR([package version not defined]))
AS_IF([test "x$PACKAGE_RELEASE" = x],
      AC_MSG_ERROR([package release not defined]))

# Automake initialization
AM_INIT_AUTOMAKE([-Wno-portability])

# Checking for build tools
AM_PATH_PYTHON([2.6])

# Checking for nosetests
AC_PATH_PROG([NOSETESTS], [nosetests])
if test "x$NOSETESTS" = "x"; then
  AC_MSG_ERROR([python-nose not found, please install it.])
fi

AC_OUTPUT([Makefile])
