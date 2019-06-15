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

import multiprocessing
import signal
import os
from sys import version_info
from os.path import join, isdir, isabs, normpath
from stat import S_IWRITE
import time
import subprocess
import shutil
from argparse import Namespace
from mx_logging import *

if version_info[0] < 3:
    import __builtin__ as builtins
    _unicode = unicode
else:
    import builtins
    _unicode = str

"""
~~~~~~~~~~~~~ OS/Arch/Platform related 
"""


def relpath_or_absolute(path, start, prefix=""):
    """
    Finds a relative path and joins it to 'prefix', or otherwise tries to use 'path' as an absolute path.
    If 'path' is not an absolute path, an error is thrown.
    """
    try:
        return join(prefix, os.path.relpath(path, start))
    except ValueError:
        if not os.path.isabs(path):
            raise ValueError('can not find a relative path to dependency and path is not absolute: ' + path)
        return path


def cpu_count():
    cpus = multiprocessing.cpu_count()
    if _opts.cpu_count:
        return cpus if cpus <= _opts.cpu_count else _opts.cpu_count
    else:
        return cpus


def is_darwin():
    return sys.platform.startswith('darwin')


def is_linux():
    return sys.platform.startswith('linux')


def is_openbsd():
    return sys.platform.startswith('openbsd')


def is_sunos():
    return sys.platform.startswith('sunos')


def is_windows():
    return sys.platform.startswith('win32')


def is_cygwin():
    return sys.platform.startswith('cygwin')


def get_os():
    """
    Get a canonical form of sys.platform.
    """
    if is_darwin():
        return 'darwin'
    elif is_linux():
        return 'linux'
    elif is_openbsd():
        return 'openbsd'
    elif is_sunos():
        return 'solaris'
    elif is_windows():
        return 'windows'
    elif is_cygwin():
        return 'cygwin'
    else:
        abort()


def is_process_alive(p):
    if isinstance(p, subprocess.Popen):
        return p.poll() is None
    assert isinstance(p, multiprocessing.Process), p
    return p.is_alive()


def send_sigquit(current_subprocess):
    for p, args in current_subprocess:

        def _isJava():
            if args:
                name = args[0].split(os.sep)[-1]
                return name == "java"
            return False

        if p is not None and is_process_alive(p) and _isJava():
            if is_windows():
                log("mx: implement me! want to send SIGQUIT to my child process")
            else:
                # only send SIGQUIT to the child not the process group
                logv('sending SIGQUIT to ' + str(p.pid))
                os.kill(p.pid, signal.SIGQUIT)
            time.sleep(0.1)


def kill_process(pid, sig):
    """
    Sends the signal `sig` to the process identified by `pid`. If `pid` is a process group
    leader, then signal is sent to the process group id.
    """
    pgid = os.getpgid(pid)
    try:
        logvv('[{} sending {} to {}]'.format(os.getpid(), sig, pid))
        if pgid == pid:
            os.killpg(pgid, sig)
        else:
            os.kill(pid, sig)
        return True
    except:
        log('Error killing subprocess ' + str(pid) + ': ' + str(sys.exc_info()[1]))
        return False


def getmtime(name):
    """
    Wrapper for builtin open function that handles long path names on Windows.
    """
    return os.path.getmtime(safe_path(path=name))


def stat(name):
    """
    Wrapper for builtin open function that handles long path names on Windows.
    """
    return os.stat(safe_path(path=name))


def lstat(name):
    """
    Wrapper for builtin open function that handles long path names on Windows.
    """
    return os.lstat(safe_path(path=name))


def open(name, mode='r'): # pylint: disable=redefined-builtin
    """
    Wrapper for builtin open function that handles long path names on Windows.
    """
    return builtins.open(safe_path(name), mode=mode)


def safe_path(path):
    """
    If not on Windows, this function returns `path`.
    Otherwise, it return a potentially transformed path that is safe for file operations.
    This works around the MAX_PATH limit on Windows:
    https://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx#maxpath
    """
    verbose = _opts.verbose if _opts is not None else False
    if is_windows():
        if verbose and '/' in path:
            warn("Forward slash in path on windows: {}".format(path))
            import traceback
            traceback.print_stack()
        path = normpath(path)
        if isabs(path):
            if path.startswith('\\\\'):
                if path[2:].startswith('?\\'):
                    # if it already has a \\?\ don't do the prefix
                    pass
                else:
                    # only a UNC path has a double slash prefix
                    path = '\\\\?\\UNC' + path
            else:
                path = '\\\\?\\' + path
        path = _unicode(path)
    return path


def copytree(src, dst, symlinks=False, ignore=None):
    shutil.copytree(safe_path(src), safe_path(dst), symlinks, ignore)


def rmtree(path, ignore_errors=False):
    path = safe_path(path=path)
    if ignore_errors:
        def on_error(*args):
            pass
    elif is_windows():
        def on_error(func, _path, exc_info):
            os.chmod(_path, S_IWRITE)
            if isdir(_path):
                os.rmdir(_path)
            else:
                os.unlink(_path)
    else:
        def on_error(*args):
            raise #pylint: disable=misplaced-bare-raise
    if isdir(path):
        shutil.rmtree(path, onerror=on_error)
    else:
        try:
            os.remove(path)
        except OSError:
            on_error(os.remove, path, sys.exc_info())

def abort(codeOrMessage, context=None, killsig=signal.SIGTERM):
    """
    Aborts the program with a SystemExit exception.
    If `codeOrMessage` is a plain integer, it specifies the system exit status;
    if it is None, the exit status is zero; if it has another type (such as a string),
    the object's value is printed and the exit status is 1.

    The `context` argument can provide extra context for an error message.
    If `context` is callable, it is called and the returned value is printed.
    If `context` defines a __abort_context__ method, the latter is called and
    its return value is printed. Otherwise str(context) is printed.
    """

    if _opts and hasattr(_opts, 'killwithsigquit') and _opts.killwithsigquit:
        logv('sending SIGQUIT to subprocesses on abort')
        send_sigquit(_currentSubprocesses)

    for p, args in _currentSubprocesses:
        if is_process_alive(p):
            if is_windows():
                p.terminate()
            else:
                kill_process(p.pid, killsig)
            time.sleep(0.1)
        if is_process_alive(p):
            try:
                if is_windows():
                    p.terminate()
                else:
                    kill_process(p.pid, signal.SIGKILL)
            except BaseException as e:
                if is_process_alive(p):
                    log_error('error while killing subprocess {0} "{1}": {2}'.format(p.pid, ' '.join(args), e))

    if _opts and hasattr(_opts, 'verbose') and _opts.verbose:
        import traceback
        traceback.print_stack()
    if context is not None:
        if callable(context):
            contextMsg = context()
        elif hasattr(context, '__abort_context__'):
            contextMsg = context.__abort_context__()
        else:
            contextMsg = str(context)
    else:
        contextMsg = ""

    if isinstance(codeOrMessage, int):
        # Log the context separately so that SystemExit
        # communicates the intended exit status
        error_message = contextMsg
        error_code = codeOrMessage
    elif contextMsg:
        error_message = contextMsg + ":\n" + codeOrMessage
        error_code = 1
    else:
        error_message = codeOrMessage
        error_code = 1
    log_error(error_message)
    raise SystemExit(error_code)


def abort_or_warn(message, should_abort, context=None):
    if should_abort:
        abort()
    else:
        warn(message, context)