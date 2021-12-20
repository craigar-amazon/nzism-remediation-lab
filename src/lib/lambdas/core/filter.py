import regex
import cfg.rules as cfgRule

def _canonIncluded(included) -> list:
    if included is None: return [".+"]
    if type(included) is str: return [included]
    return list(included)

def _canonExcluded(excluded) -> list:
    if excluded is None: return []
    if type(excluded) is str: return [excluded]
    return list(excluded)


def acceptResourceId(configRuleName, action, accountName, resourceId) -> bool:
    included = cfgRule.includedResourceIds(configRuleName, action, accountName)
    excluded = cfgRule.excludedResourceIds(configRuleName, action, accountName)
    inList = _canonIncluded(included)
    exList = _canonExcluded(excluded)
    matchIn = False
    for inPattern in inList:
        if regex.fullmatch(inPattern, resourceId):
            matchIn = True
            break
    if not matchIn: return False
    matchEx = False
    for exPattern in exList:
        if regex.fullmatch(exPattern, resourceId):
            matchEx = True
            break
    if matchEx: return False
    return True


