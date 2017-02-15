from __future__ import unicode_literals

import sys

from pre_commit.xargs import xargs


ENVIRONMENT_DIR = None
GREP = 'ggrep' if sys.platform == 'darwin' else 'grep'


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
        is_local_hook=False,
):
    """Installation for pcre type is a noop."""
    raise AssertionError('Cannot install pcre repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    # For PCRE the entry is the regular expression to match
    cmd = (GREP, '-H', '-n', '-P') + tuple(hook['args']) + (hook['entry'],)

    # Grep usually returns 0 for matches, and nonzero for non-matches so we
    # negate it here.
    return xargs(cmd, file_args, negate=True)
