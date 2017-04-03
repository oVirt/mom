# Memory Overcommitment Manager
# Copyright (C) 2017 Martin Sivak, Red Hat
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

import traceback
import time
import functools
import threading

# Cache return values with expiration
def memoize(expiration):
    def decorator(obj):
        lock = threading.Lock()
        cache = obj._cache = {}
        timestamps = obj._timestamps = {}

        @functools.wraps(obj)
        def memoizer(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time.time()

            # use absolute value of the time difference to avoid issues
            # with time changing to the past

            with lock:
                if key not in cache or abs(now - timestamps[key]) > expiration:
                    cache[key] = obj(*args, **kwargs)
                    timestamps[key] = now
                return cache[key]
        return memoizer
    return decorator

class vdsmException(Exception):

    def __init__(self, response, logger):
        try:
            self.msg = response['status'].get('message', response)
        except (AttributeError, KeyError):
            self.msg = response
        self.logger = logger

    def handle_exception(self):
        "Handle exception in a nice way. Just report the message and try again later."
        self.logger.error(self.msg)
        self.logger.debug(traceback.format_exc())