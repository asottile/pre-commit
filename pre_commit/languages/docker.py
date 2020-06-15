import functools
import hashlib
import os
from typing import Sequence
from typing import Tuple

import pre_commit.constants as C
from pre_commit.hook import Hook
from pre_commit.languages import helpers
from pre_commit.prefix import Prefix
from pre_commit.util import CalledProcessError
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = 'docker'
PRE_COMMIT_LABEL = 'PRE_COMMIT'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def md5(s: str) -> str:  # pragma: win32 no cover
    return hashlib.md5(s.encode()).hexdigest()


def docker_tag(prefix: Prefix) -> str:  # pragma: win32 no cover
    md5sum = md5(os.path.basename(prefix.prefix_dir)).lower()
    return f'pre-commit-{md5sum}'


def docker_is_running() -> bool:  # pragma: win32 no cover
    try:
        cmd_output_b('docker', 'ps')
    except CalledProcessError:
        return False
    else:
        return True


def assert_docker_available() -> None:  # pragma: win32 no cover
    assert docker_is_running(), (
        'Docker is either not running or not configured in this environment'
    )


def build_docker_image(
        prefix: Prefix,
        *,
        pull: bool,
) -> None:  # pragma: win32 no cover
    cmd: Tuple[str, ...] = (
        'docker', 'build',
        '--tag', docker_tag(prefix),
        '--label', PRE_COMMIT_LABEL,
    )
    if pull:
        cmd += ('--pull',)
    # This must come last for old versions of docker.  See #477
    cmd += ('.',)
    helpers.run_setup_cmd(prefix, cmd)


def install_environment(
        prefix: Prefix, version: str, additional_dependencies: Sequence[str],
) -> None:  # pragma: win32 no cover
    helpers.assert_version_default('docker', version)
    helpers.assert_no_additional_deps('docker', additional_dependencies)
    assert_docker_available()

    directory = prefix.path(
        helpers.environment_dir(ENVIRONMENT_DIR, C.DEFAULT),
    )

    # Docker doesn't really have relevant disk environment, but pre-commit
    # still needs to cleanup its state files on failure
    with clean_path_on_failure(directory):
        build_docker_image(prefix, pull=True)
        os.mkdir(directory)


def _docker_is_rootless() -> bool:  # pragma: win32 no cover
    returncode, stdout, stderr = cmd_output(
        'docker', 'system', 'info',
    )
    for line in stdout.splitlines():
        # rootless docker has "rootless"
        # rootless podman has "rootless: true"
        if line.strip().startswith('rootless'):
            if 'false' not in line:
                return True
            break
    return False


@functools.lru_cache(maxsize=1)
def docker_is_rootless() -> bool:  # pragma: win32 no cover
    return _docker_is_rootless()


def get_docker_user() -> Tuple[str, ...]:  # pragma: win32 no cover
    if docker_is_rootless():
        return ()
    try:
        return ('-u', f'{os.getuid()}:{os.getgid()}')
    except AttributeError:
        return ()


def docker_cmd() -> Tuple[str, ...]:  # pragma: win32 no cover
    return (
        'docker', 'run',
        '--rm',
        *get_docker_user(),
        # https://docs.docker.com/engine/reference/commandline/run/#mount-volumes-from-container-volumes-from
        # The `Z` option tells Docker to label the content with a private
        # unshared label. Only the current container can use a private volume.
        '-v', f'{os.getcwd()}:/src:rw,Z',
        '--workdir', '/src',
    )


def run_hook(
        hook: Hook,
        file_args: Sequence[str],
        color: bool,
) -> Tuple[int, bytes]:  # pragma: win32 no cover
    assert_docker_available()
    # Rebuild the docker image in case it has gone missing, as many people do
    # automated cleanup of docker images.
    build_docker_image(hook.prefix, pull=False)

    hook_cmd = hook.cmd
    entry_exe, cmd_rest = hook.cmd[0], hook_cmd[1:]

    entry_tag = ('--entrypoint', entry_exe, docker_tag(hook.prefix))
    cmd = docker_cmd() + entry_tag + cmd_rest
    return helpers.run_xargs(hook, cmd, file_args, color=color)
