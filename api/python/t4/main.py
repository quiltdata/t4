"""
Parses the command-line arguments and runs a command.
"""

import argparse
import sys

from . import session
from .util import QuiltException


def create_parser():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(metavar="<command>")
    subparsers.required = True

    # login
    shorthelp = "Log in to configured Quilt server"
    login_p = subparsers.add_parser("login", description=shorthelp, help=shorthelp)
    login_p.set_defaults(func=session.login)

    # logout
    shorthelp = "Log out of current Quilt server"
    logout_p = subparsers.add_parser("logout", description=shorthelp, help=shorthelp)
    logout_p.set_defaults(func=session.logout)

    return parser

def main(args=None):
    parser = create_parser()
    args = parser.parse_args(args)

    kwargs = vars(args)
    func = kwargs.pop('func')

    try:
        func(**kwargs)
    except QuiltException as ex:
        print(ex.message, file=sys.stderr)

    return 0
