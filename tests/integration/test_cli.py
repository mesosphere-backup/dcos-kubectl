from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(
        ['dcos-kubernetes', 'kubernetes', '--help'])

    assert returncode == 0
    assert stdout == b"""DCOS Kubernetes Subcommand

Usage:
    dcos kubectl parameters...
"""
    assert stderr == b''
