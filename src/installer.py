import argparse

import cmds.precheck as cmd_precheck
import cmds.initialise as cmd_initialise

def sub_precheck(args):
    try:
        print("Verifying...")
        cmd_precheck.handler(args)
    except Exception as e:
        print("Verification failed")
        print(e)

def sub_init(args):
    try:
        print("Initialising...")
        cmd_initialise.handler(args)
    except Exception as e:
        print("Initialisation failed")
        print(e)

def sub_rules(args):
    print("Rules.."+args)


topparser = argparse.ArgumentParser()
subparsers = topparser.add_subparsers(help="sub-command help")
parser_precheck = subparsers.add_parser('precheck', help="precheck help")
parser_precheck.set_defaults(func=sub_precheck)
parser_init = subparsers.add_parser('init', help="init help")
parser_init.add_argument('--cpack-prefix',dest='cpackPrefix', required=True, default="NZISM", help="Conformance Pack Prefix")
parser_init.set_defaults(func=sub_init)
parser_rules = subparsers.add_parser('rules', help="rules help")
parser_rules.set_defaults(func=sub_rules)
args = topparser.parse_args()
args.func(args)

