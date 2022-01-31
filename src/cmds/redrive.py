from lib.rdq import Profile
from lib.rdq.svccfg import CfgClient
from lib.rdq.svcorg import OrganizationClient
import lib.lambdas.core.filter as filter
import lib.lambdas.core.ruleselector as rulesel

import cfg.core

import cmds.cfgutil as cfgutil

def get_aggregator_name(args, isLocal):
    if isLocal: return None
    argName = args.aggregator 
    if len(argName) > 0:
        return None if argName == 'local' else argName
    cfgName = cfg.core.coreRedriveAggregatorName()
    if (cfgName is None) or len(cfgName) == 0: return None
    return cfgName

def accept_rule(ruleName, accountName):
    action = rulesel.ActionRemediate
    optBaseName = rulesel.getRuleBaseName(ruleName)
    if not optBaseName: return False
    if not rulesel.isActionEnabled(action, optBaseName, accountName): return False
    optFolder = rulesel.getRuleCodeFolder(optBaseName, action, accountName)
    if not optFolder: return False
    return True

def accept_resource(ruleName, accountName, resourceId):
    action = rulesel.ActionRemediate
    optBaseName = rulesel.getRuleBaseName(ruleName)
    if not optBaseName: return False
    return filter.acceptResourceId(optBaseName, action, accountName, resourceId)


def pushmessage(ruleName, accountName, resourceId):
    print("Pushing {} {}: {} {}".format(accountName, ruleName, resourceId))

def process(args):
    isLocal = args.forcelocal or cfgutil.isLandingZoneSearchDisabled()
    previewfilters = args.previewfilters
    aggregatorName = get_aggregator_name(args, isLocal)
    if aggregatorName:
        print("Redrive will read aggregator: {}".format(aggregatorName))
    else:
        print("Redrive will read config rules from this account only")
    
    profile = Profile()
    cfgc = CfgClient(profile)
    orgc = OrganizationClient(profile)
    agenda = cfgc.selectNonCompliantAccountAgenda(aggregatorName)
    for accountId in agenda.accountIds():
        if isLocal:
            accountName = 'local'
            accountIsActive = True
        else:
            accountDesc = orgc.getAccountDescriptor(accountId)
            accountName = accountDesc.accountName
            accountIsActive = accountDesc.isActive
        if not accountIsActive: continue
        for regionName in agenda.regionNames(accountId):
            configRuleNameSet = agenda.configRuleNameSet(accountId, regionName)
            for ruleName in configRuleNameSet:
                print("{} {}".format(accountName, ruleName))
                if not accept_rule(ruleName, accountName): continue
                resourceDescriptors = cfgc.listNonCompliantResources(ruleName, aggregatorName, accountId, regionName)
                for rd in resourceDescriptors:
                    if not accept_resource(ruleName, accountName, rd.resourceId): continue
                    print("> {} {}".format(rd.resourceType, rd.resourceId))
                    if previewfilters: continue
                    pushmessage(ruleName, accountName, rd.resourceId)

