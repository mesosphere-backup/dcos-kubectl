from common import exec_command


def test_help():
    returncode, stdout, stderr = exec_command(
        ['dcos-helloworld', 'helloworld', '--help'])

    assert returncode == 0
    assert stdout == b"""DCOS HelloWorld Example Subcommand

Usage:
    dcos helloworld info

Options:
    --help           Show this screen
    --version        Show version
"""
    assert stderr == b''
