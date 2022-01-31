import cfg.rules as cfgRules

ActionRemediate = 'remediate'
ActionBaseline = 'baseline'

def getRuleBaseName(qualifiedName):
    spos = qualifiedName.find("-conformance-pack-")
    if spos <= 0: return None
    return qualifiedName[0:spos]

def getRuleCodeFolder(ruleBaseName, action, targetAccountName):
    return cfgRules.codeFolder(ruleBaseName, action, targetAccountName)

def isActionEnabled(action, ruleBaseName, targetAccountName):
    if action == ActionRemediate: return cfgRules.canRemediate(ruleBaseName, targetAccountName)
    if action == ActionBaseline: return cfgRules.canBaseline(ruleBaseName, targetAccountName)
    return False
