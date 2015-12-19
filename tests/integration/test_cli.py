from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(
        ['dcos-kubectl', 'kubectl', '--help'])

    assert returncode == 0

    expected_first_line = b'kubectl controls the Kubernetes cluster manager'
    assert stdout.startswith(expected_first_line)
    assert stderr == b''
