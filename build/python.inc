#
# otopi -- plugable installer
# Copyright (C) 2012-2013 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#

PYTHON_SYNTAX_CHECK_FILES = $(srcdir)/*.py

python-syntax-check:
if PYTHON_SYNTAX_CHECK
	if [ -n "$(PYFLAKES)" ]; then \
		$(PYFLAKES) $(PYTHON_SYNTAX_CHECK_FILES); \
	fi
	if [ -n "$(PEP8)" ]; then \
		$(PEP8) $(PYTHON_SYNTAX_CHECK_FILES); \
	fi
endif

python-clean:
	rm -rf $(srcdir)/__pycache__ __pycache__
	rm -f $(srcdir)/*.pyc $(srcdir)/*.pyo *.pyc *.pyo
