import argparse

import lib.base
import lib.rdq

import cmds.precheck
import cmds.builder


helpLocal = '''
Disables the landing zone search path in the cfg.roles.py file for all sub-commands, including 'init' and 'code'.
Setting this flag performs a local-account-only installation, even if the account is part of a landing zone. 
Either specify this flag, or set the landing zone search path to an empty list, when installing into a standalone account.
'''

helpPrecheck = '''
Check whether the pre-requisites for installation are satisfied.
'''

helpInit = '''
Install the baseline remediation pack into your landing zone or stand-alone account.
'''

helpInitOU = '''
A space-separated list of the Organization Units (OUs) into which compliance event forwarding rules will be deployed.
This overrides the list provided in the cfg.org.py file.
Specify '--ous Root' to forward compliance events for the whole Organization.
You can specify an OU using: the OU identifier (e.g. ou-cafe-8ajx3n7c), the OU name (e.g. Security), or the full OU path,
starting with Root, and using / as a separator (e.g Root/Infra/Prod). Use a full path if your OU naming convention allows
local re-use of OU names (e.g. --ous Root/Infra/Prod  Root/Apps/Prod).
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
Remove the remediation pack from your landing zone or stand-alone account.
'''

helpRemoveCmks = '''
Include the scheduled removal of Customer Managed Keys (CMKs) in the resource removal process.
A retained CMK will be re-used if the pack is subsequently re-installed with the same CMK alias.
'''

helpView = '''
View the remediation pack resources.
'''

helpViewForwarders = '''
View the compliance event forwarder stacks.
'''


def main(subcmd):
    if subcmd == 'init': cmds.builder.init(args)
    elif subcmd == 'code': cmds.builder.code(args)
    elif subcmd == 'remove': cmds.builder.remove(args)
    elif subcmd == 'view': cmds.builder.view(args)


topparser = argparse.ArgumentParser()
topparser.add_argument('--verbose', dest='verbose', action='store_true')
topparser.add_argument('--local',dest='forcelocal', action='store_true', help=helpLocal)
subparsers = topparser.add_subparsers(dest='subcmd', required=True)
parser_precheck = subparsers.add_parser('precheck', help=helpPrecheck)
parser_init = subparsers.add_parser('init', help=helpInit)
parser_init.add_argument('--ous',dest='ous', nargs='+', help=helpInitOU)
parser_code = subparsers.add_parser('code', help=helpCode)
parser_code.add_argument('--core',dest='core', action='store_true', help=helpCodeCore)
parser_code.add_argument('--rules',dest='rules', action='store_true', help=helpCodeRules)
parser_remove = subparsers.add_parser('remove', help=helpRemove)
parser_remove.add_argument('--remove-cmks',dest='removecmks', action='store_true', help=helpRemoveCmks)
parser_view = subparsers.add_parser('view', help=helpView)
parser_view.add_argument('--forwarders',dest='forwarders', action='store_true', help=helpViewForwarders)
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


