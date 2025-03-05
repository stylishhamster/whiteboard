import os
import pytest
import subprocess
import testinfra

local_host = testinfra.get_host("local://")
check_output = local_host.check_output

TAIL_DEV_NULL = "tail -f /dev/null"


@pytest.fixture()
def run_and_stream_command_output():
    def run_and_stream_command_output_inner(command, verbose=False):
        print("Running", command)
        build_env = os.environ.copy()
        build_env["PIHOLE_DOCKER_TAG"] = version
        build_result = subprocess.Popen(
            command.split(),
            env=build_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        )
        if verbose:
            while build_result.poll() is None:
                for line in build_result.stdout:
                    print(line, end="")
        build_result.wait()
        if build_result.returncode != 0:
            print(f"       [i] Error running: {command}")
            print(build_result.stderr)

    return run_and_stream_command_output_inner


@pytest.fixture()
def args_volumes():
    return "-v /dev/null:/etc/pihole/adlists.list"


@pytest.fixture()
def args_env():
    return '-e FTLCONF_LOCAL_IPV4="127.0.0.1"'


@pytest.fixture()
def args(args_volumes, args_env):
    return "{} {}".format(args_volumes, args_env)


@pytest.fixture()
def test_args():
    """test override fixture to provide arguments separate from our core args"""
    return ""


def docker_generic(request, _test_args, _args, _image, _cmd, _entrypoint):
    # assert 'docker' in check_output('id'), "Are you in the docker group?"
    # Always appended PYTEST arg to tell pihole we're testing
    if "pihole" in _image and "PYTEST=1" not in _args:
        _args = "{} -e PYTEST=1".format(_args)
    docker_run = "docker run -d -t {args} {test_args} {entry} {image} {cmd}".format(
        args=_args, test_args=_test_args, entry=_entrypoint, image=_image, cmd=_cmd
    )
    # Print a human runable version of the container run command for faster debugging
    print(docker_run.replace("-d -t", "--rm -it").replace(TAIL_DEV_NULL, "bash"))
    docker_id = check_output(docker_run)

    def teardown():
        check_output("docker logs {}".format(docker_id))
        check_output("docker rm -f {}".format(docker_id))

    request.addfinalizer(teardown)
    docker_container = testinfra.backend.get_backend(
        "docker://" + docker_id, sudo=False
    )
    docker_container.id = docker_id

    return docker_container


@pytest.fixture
def docker(request, test_args, args, image, cmd, entrypoint):
    """One-off Docker container run"""
    return docker_generic(request, test_args, args, image, cmd, entrypoint)


@pytest.fixture(scope="module")
def docker_persist(
    request,
    persist_test_args,
    persist_args,
    persist_image,
    persist_cmd,
    persist_entrypoint,
    dig,
):
    """
    Persistent Docker container for multiple tests, instead of stopping container after one test
    Uses DUP'd module scoped fixtures because smaller scoped fixtures won't mix with module scope
    """
    persistent_container = docker_generic(
        request,
        persist_test_args,
        persist_args,
        persist_image,
        persist_cmd,
        persist_entrypoint,
    )
    """ attach a dig container for lookups """
    persistent_container.dig = dig(persistent_container.id)
    return persistent_container


@pytest.fixture
def entrypoint():
    return ""


@pytest.fixture()
def version():
    return os.environ.get("GIT_TAG", None)


@pytest.fixture()
def tag(version):
    return "{}".format(version)


@pytest.fixture
def webserver(tag):
    """TODO: this is obvious without alpine+nginx as the alternative, remove fixture, hard code lighttpd in tests?"""
    return "lighttpd"


@pytest.fixture()
def image(tag):
    image = "pihole"
    return "{}:{}".format(image, tag)


@pytest.fixture()
def cmd():
    return TAIL_DEV_NULL


@pytest.fixture(scope="module")
def persist_version():
    return version


@pytest.fixture(scope="module")
def persist_args_dns():
    return "--dns 127.0.0.1 --dns 1.1.1.1"


@pytest.fixture(scope="module")
def persist_args_volumes():
    return "-v /dev/null:/etc/pihole/adlists.list"


@pytest.fixture(scope="module")
def persist_args_env():
    return '-e ServerIP="127.0.0.1"'


@pytest.fixture(scope="module")
def persist_args(persist_args_volumes, persist_args_env):
    return "{} {}".format(persist_args_volumes, persist_args_env)


@pytest.fixture(scope="module")
def persist_test_args():
    """test override fixture to provide arguments separate from our core args"""
    return ""


@pytest.fixture(scope="module")
def persist_tag(persist_version):
    return "{}".format(persist_version)


@pytest.fixture(scope="module")
def persist_webserver(persist_tag):
    """TODO: this is obvious without alpine+nginx as the alternative, remove fixture, hard code lighttpd in tests?"""
    return "lighttpd"


@pytest.fixture(scope="module")
def persist_image(persist_tag):
    image = "pihole"
    return "{}:{}".format(image, persist_tag)


@pytest.fixture(scope="module")
def persist_cmd():
    return TAIL_DEV_NULL


@pytest.fixture(scope="module")
def persist_entrypoint():
    return ""


@pytest.fixture
def slow():
    """
    Run a slow check, check if the state is correct for `timeout` seconds.
    """
    import time

    def _slow(check, timeout=20):
        timeout_at = time.time() + timeout
        while True:
            try:
                assert check()
            except AssertionError as e:
                if time.time() < timeout_at:
                    time.sleep(1)
                else:
                    raise e
            else:
                return

    return _slow


@pytest.fixture(scope="module")
def dig():
    """separate container to link to pi-hole and perform lookups"""
    """ a docker pull is faster than running an install of dnsutils """

    def _dig(docker_id):
        args = "--link {}:test_pihole".format(docker_id)
        image = "azukiapp/dig"
        cmd = TAIL_DEV_NULL
        dig_container = docker_generic(request, "", args, image, cmd, "")
        return dig_container

    return _dig


@pytest.fixture
def running_pihole(docker_persist, slow, persist_webserver):
    """Persist a fully started docker-pi-hole to help speed up subsequent tests"""
    slow(lambda: docker_persist.run("pgrep pihole-FTL").rc == 0)
    slow(lambda: docker_persist.run("pgrep lighttpd").rc == 0)
    return docker_persist
