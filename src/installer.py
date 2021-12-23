import argparse

import lib.base
import lib.rdq

import cmds.precheck
import cmds.initialise

helpPrecheck = '''
Check whether the pre-requisites for installation are satisfied.
'''

helpInit = '''
Install the default remediation pack into your landing zone or test environment.
'''

helpInitLocal = '''
Forces a local-account-only installation of the remediation pack when an Organization is detected.
If the remediation pack is installed in a stand-alone account, installation will always be local.
'''

helpCode = '''
Upload and deploy lambda code and configuration.
'''

helpCodeCore = '''
Upload and deploy core lambda code and configuration from the 'core' sub-folders
'''
helpCodeRules = '''
Upload and deploy all lambda code and configuration from the 'rules' sub-folders
'''

def main():
    topparser = argparse.ArgumentParser()
    subparsers = topparser.add_subparsers(dest='subcmd', required=True)
    parser_precheck = subparsers.add_parser('precheck', help=helpPrecheck)
    parser_init = subparsers.add_parser('init', help=helpInit)
    parser_init.add_argument('--local',dest='forcelocal', action='store_true', help=helpInitLocal)
    parser_code = subparsers.add_parser('code', help=helpCode)
    parser_code.add_argument('--core',dest='core', action='store_true', help=helpCodeCore)
    parser_code.add_argument('--rules',dest='rules', action='store_true', help=helpCodeRules)
    args = topparser.parse_args()
    subcmd = args.subcmd
    if subcmd == 'init': cmds.initialise.handler(args)


lib.base.initLogging(defaultLevel='WARNING', announceLogLevel=False)
try:
    main()
except lib.rdq.RdqCredentialsWarning as e:
    print(e.message)
except lib.base.ConfigError as e:
    print(e.message)
