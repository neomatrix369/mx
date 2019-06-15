from argparse import Namespace

global _opts
_opts = Namespace()

# Makes the current subprocess accessible to the abort() function
# This is a list of tuples of the subprocess.Popen or
# multiprocessing.Process object and args.
global _currentSubprocesses
_currentSubprocesses = []