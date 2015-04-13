"""DCOS HelloWorld Example Subcommand

Usage:
    dcos helloworld --info

Options:
    --help           Show this screen
    --version        Show version
"""
import docopt
from dcos_helloworld import constants


def main():
    args = docopt.docopt(
        __doc__,
        version='dcos-marathon version {}'.format(constants.version))

    if args['helloworld'] and args['--info']:
        print('Example of a DCOS subcommand')
    else:
        print(__doc__)
        return 1

    return 0
