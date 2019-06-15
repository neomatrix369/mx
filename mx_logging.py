#
# ----------------------------------------------------------------------------------------------------
#
# Copyright (c) 2007, 2015, Oracle and/or its affiliates. All rights reserved.
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
#
# This code is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 only, as
# published by the Free Software Foundation.
#
# This code is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# version 2 for more details (a copy is included in the LICENSE file that
# accompanied this code).
#
# You should have received a copy of the GNU General Public License version
# 2 along with this work; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Please contact Oracle, 500 Oracle Parkway, Redwood Shores, CA 94065 USA
# or visit www.oracle.com if you need additional information or have any
# questions.
#
# ----------------------------------------------------------------------------------------------------
#

from mx_shared import _opts, _currentSubprocesses
import sys
from mx_system import *

"""
~~~~~~~~~~~~~ Logging 
"""


def logv(msg=None):
    if vars(_opts).get('verbose') is None:
        def _deferrable():
            logv(msg)
        _opts._parsed_deferrables.append(_deferrable)
        return

    if _opts.verbose:
        log(msg)


def logvv(msg=None):
    if vars(_opts).get('very_verbose') is None:
        def _deferrable():
            logvv(msg)
        _opts._parsed_deferrables.append(_deferrable)
        return

    if _opts.very_verbose:
        log(msg)


def log(msg=None):
    """
    Write a message to the console.
    All script output goes through this method thus allowing a subclass
    to redirect it.
    """
    if vars(_opts).get('quiet'):
        return
    if msg is None:
        print()
    else:
        # https://docs.python.org/2/reference/simple_stmts.html#the-print-statement
        # > A '\n' character is written at the end, unless the print statement
        # > ends with a comma.
        #
        # In CPython, the normal print statement (without comma) is compiled to
        # two bytecode instructions: PRINT_ITEM, followed by PRINT_NEWLINE.
        # Each of these bytecode instructions is executed atomically, but the
        # interpreter can suspend the thread between the two instructions.
        #
        # If the print statement is followed by a comma, the PRINT_NEWLINE
        # instruction is omitted. By manually adding the newline to the string,
        # there is only a single PRINT_ITEM instruction which is executed
        # atomically, but still prints the newline.
        print(str(msg), end='\n')


# https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
_ansi_color_table = {
    'black' : '30',
    'red' : '31',
    'green' : '32',
    'yellow' : '33',
    'blue' : '34',
    'magenta' : '35',
    'cyan' : '36'
    }


def colorize(msg, color='red', bright=True, stream=sys.stderr):
    """
    Wraps `msg` in ANSI escape sequences to make it print to `stream` with foreground font color
    `color` and brightness `bright`. This method returns `msg` unchanged if it is None,
    if it already starts with the designated escape sequence or the execution environment does
    not support color printing on `stream`.
    """
    if msg is None:
        return None
    code = _ansi_color_table.get(color, None)
    if code is None:
        abort('Unsupported color: ' + color + '.\nSupported colors are: ' + ', '.join(_ansi_color_table.keys()))
    if bright:
        code += ';1'
    color_on = '\033[' + code + 'm'
    if not msg.startswith(color_on):
        isUnix = sys.platform.startswith('linux') or sys.platform in ['darwin', 'freebsd']
        if isUnix and hasattr(stream, 'isatty') and stream.isatty():
            return color_on + msg + '\033[0m'
    return msg


def log_error(msg=None):
    """
    Write an error message to the console.
    All script output goes through this method thus allowing a subclass
    to redirect it.
    """
    if msg is None:
        print(sys.stderr, file=sys.stderr)
    else:
        print(colorize(str(msg), stream=sys.stderr), file=sys.stderr)


def warn(msg, context=None):
    if _opts.warn:
        if context is not None:
            if callable(context):
                contextMsg = context()
            elif hasattr(context, '__abort_context__'):
                contextMsg = context.__abort_context__()
            else:
                contextMsg = str(context)
            msg = contextMsg + ":\n" + msg
        print(colorize('WARNING: ' + msg, color='magenta', bright=True, stream=sys.stderr), file=sys.stderr)