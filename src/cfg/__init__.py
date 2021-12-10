class RuleTable:
    def __init__(self):
        self._ruleTable = {}

    def lookup(self, configRuleName :str, key :str, defaultValue :str=None, action :str=None, accountName :str=None):
        rule :dict = self._ruleTable.get(configRuleName)
        if not rule: return None
        if accountName:
            key2 = "{}.{}.{}".format(key, action, accountName)
            if key2 in rule: return rule[key2]
        if action:
            key1 = "{}.{}".format(key, action)
            if key1 in rule: return rule[key1]
        if key in rule: return rule[key]
        return defaultValue

    def put(self, configRuleName :str, config: dict):
        self._ruleTable[configRuleName] = config

    def update(self, ruleTable: dict):
        self._ruleTable.update(ruleTable)
