import cfn_core as cfn
import cfn_iam as ci
import cfn_eb as ce

import util_cfn as uc

stackSetName = "ConfigRuleComplianceChangeForwarder"
stackSetDescription = "Config Rule compliance change forwarder"
eventBusName = 'default'
ruleName = 'ComplianceChange'
ruleDescription = "Config Rule Compliance Change"
targetId = "centralBus"
policyName = 'CentralBusForwarderPolicy'
roleName = 'ConfigRuleComplianceChangeForwarderRole'
roleDescription = 'Allow config rule compliance chance events to be forwarded to central event bus'
rTargetEventBus = "arn:aws:events:ap-southeast-2:746869318262:event-bus/NZISM-AutoRemediation"
regions = ['ap-southeast-2']
rootId = 'r-djii'
ouId1 = 'ou-djii-q1v40guj'
ouIdSec = 'ou-djii-yzvg6i7l'
orgIds = [ rootId ]

propForwarderPermission = ci.propPermission(
    policyName,
    ci.propPolicyDocument(
        [ ci.propAllowPutEvent(rTargetEventBus)]
    )
)

rRole = ci.resourceRole(
    roleName,
    roleDescription,
    ci.propEventBridgeServicePolicy(),
    [ propForwarderPermission ]
)

eventPatternMap = ce.eventPatternConfigComplianceChange()
targets = [ ce.propTarget(targetId, rTargetEventBus, cfn.arn('rRole')) ]
rEventRule = ce.resourceRule(eventBusName, ruleName, eventPatternMap, targets)

resourceMap = {
    'rRole': rRole, 
    'rEventRule': rEventRule 
}

# uc.deleteStackSetForOrganization(stackSetName, orgIds, regions)

templateMap = cfn.template(stackSetDescription, resourceMap)
ss = uc.declareStackSetIdForOrganization(stackSetName, templateMap, stackSetDescription, orgIds, regions)
print(ss)
# ctapp1, ctaudit, 211875017857
