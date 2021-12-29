import argparse

import lib.base
import lib.rdq

import cmds.precheck
import cmds.builder

helpPrecheck = '''
Check whether the pre-requisites for installation are satisfied.
'''

helpInit = '''
Install the baseline remediation pack into your landing zone or stand-alone account.
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

helpRemove = '''
Remove the remediation pack namespace from your landing zone or stand-alone account.
'''

helpRemoveCmks = '''
Include the scheduled removal of Customer Managed Keys (CMKs) in the resource removal process.
A retained CMK will be re-used if the pack is subsequently re-installed with the same CMK alias.
'''

def main(subcmd):
    if subcmd == 'init': cmds.builder.init(args)
    elif subcmd == 'code': cmds.builder.code(args)
    elif subcmd == 'remove': cmds.builder.remove(args)


topparser = argparse.ArgumentParser()
topparser.add_argument('--verbose', dest='verbose', action='store_true')
subparsers = topparser.add_subparsers(dest='subcmd', required=True)
parser_precheck = subparsers.add_parser('precheck', help=helpPrecheck)
parser_init = subparsers.add_parser('init', help=helpInit)
parser_init.add_argument('--local',dest='forcelocal', action='store_true', help=helpInitLocal)
parser_code = subparsers.add_parser('code', help=helpCode)
parser_code.add_argument('--core',dest='core', action='store_true', help=helpCodeCore)
parser_code.add_argument('--rules',dest='rules', action='store_true', help=helpCodeRules)
parser_remove = subparsers.add_parser('remove', help=helpRemove)
parser_remove.add_argument('--remove-cmks',dest='removecmks', action='store_true', help=helpRemoveCmks)
args = topparser.parse_args()
if args.verbose:
    lib.base.initLogging(defaultLevel='INFO', announceLogLevel=True)
else:
    lib.base.initLogging(defaultLevel='WARNING', announceLogLevel=False)
try:
    main(args.subcmd)
except lib.rdq.RdqCredentialsWarning as e:
    print(e.message)
except lib.base.ConfigError as e:
    print(e.message)


