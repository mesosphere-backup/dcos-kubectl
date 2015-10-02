from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(
        ['dcos-kubernetes', 'kubernetes', '--help'])

    assert returncode == 0
    assert stdout.startswith("kubectl controls the Kubernetes cluster manager")
    assert stderr == b''
