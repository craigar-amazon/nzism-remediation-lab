import cfn_core as cfn
import cfn_iam as ci
import cfn_eb as ce

import util_cfn as uc
import util_iam as ui
import util_lambda as ul
import util_eb as ue
import util_org as uo


def get_lambda_config():
    return {
        'Runtime': 'python3.8',
        'Handler': 'lambda_function.lambda_handler',
        'Timeout': 600,
        'Description': "Remediates non-compliant resources based on NZISM controls",
        'MemorySize': 128
    }

def get_assume_role_policy_json(roleName):
    return {
        'Version': "2012-10-17",
        'Statement': [
            {
                'Effect': "Allow",
                'Action': "sts:AssumeRole",
                'Resource': [
                    "arn:aws:iam::*:role/"+roleName
                ]
            }
        ]
    }


def test_stackset():
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


def test_deploy_lambda():
    lambdaFunctionName = "NZISMAutoRemediation"
    lambdaRoleName = 'aws-controltower-AuditAdministratorRole'
    lambdaRole = ui.getIamRole(lambdaRoleName)
    if not lambdaRole:
        raise Exception('Required role '+lambdaRoleName+" does not exist")
    lambdaCfg = get_lambda_config()
    lambdaArn = ul.declareLambdaFunctionArn(lambdaFunctionName, lambdaRole['Arn'], lambdaCfg, './lambda')
    print("Deployed LambdaArn="+lambdaArn)
    return lambdaArn

def test_lzwalk():
    # lz1 = describeLandingZone(['Legacy-Production'])
    # lz1 = describeLandingZone([], 'core', 'security', 'log-archive')

    landingZone = uo.describeLandingZone()
    organizationId = landingZone['OrganizationId']
    print("Organization Id=" + organizationId)
    return organizationId


def test_deploy_local_eventBus(lambdaArn, organizationId):

    eventBusName = 'NZISM-AutoRemediation'
    ruleName = 'ComplianceChange'
    ruleDescription = "Config Rule Compliance Change"
    eventPattern = {
    'source': ["aws.config"],
    'detail-type': ["Config Rules Compliance Change"]
    }
    maxAgeSecs = 12 * 3600
    ebArn = ue.declareEventBusArn(eventBusName)
    ue.putEventBusPermissionForOrganization(eventBusName, organizationId)
    print(ebArn)
    ruleArn = ue.putEventBusRuleArn(ebArn, ruleName, eventPattern, ruleDescription)
    ul.declareLambdaPolicyForEventRule(lambdaArn, ruleArn)

    ue.putEventBusLambdaTarget(ebArn, ruleName, lambdaArn, maxAgeSecs)  

    # deleteEventBus(eventBusName, [ruleName])


def test_exec_lambda():
    lambdaFunctionName = "NZISMAutoRemediation"
    payload = {
        'source': "installer"
    }
    ul.invokeLambdaFunction(lambdaFunctionName, payload)


test_deploy_lambda()


def sample_cloudwatch_log_group_encrypted():
    return {
        'version': '0',
        'id': 'cae8895f-83ec-ce79-77a1-56b48a75f1ff',
        'detail-type': 'Config Rules Compliance Change',
        'source': 'aws.config',
        'account': '119399605612',
        'time': '2021-10-26T23:23:41Z',
        'region': 'ap-southeast-2',
        'resources': [],
        'detail': {
            'resourceId': 'app1loggroup',
            'awsRegion': 'ap-southeast-2',
            'awsAccountId': '119399605612',
            'configRuleName': 'cloudwatch-log-group-encrypted-conformance-pack-n0q8yfwsp',
            'recordVersion': '1.0',
            'configRuleARN': 'arn:aws:config:ap-southeast-2:119399605612:config-rule/aws-service-rule/config-conforms.amazonaws.com/config-rule-j5yvzl',
            'messageType': 'ComplianceChangeNotification',
            'newEvaluationResult': {
                'evaluationResultIdentifier': {
                    'evaluationResultQualifier': {
                        'configRuleName': 'cloudwatch-log-group-encrypted-conformance-pack-n0q8yfwsp',
                        'resourceType': 'AWS::Logs::LogGroup',
                        'resourceId': 'app1loggroup'
                    },
                    'orderingTimestamp': '2021-10-26T23:23:30.964Z'
                },
                'complianceType': 'NON_COMPLIANT',
                'resultRecordedTime': '2021-10-26T23:23:40.890Z',
                'configRuleInvokedTime': '2021-10-26T23:23:40.456Z',
                'annotation': 'This log group is not encrypted.'
            },
            'notificationCreationTime': '2021-10-26T23:23:41.160Z',
            'resourceType': 'AWS::Logs::LogGroup'
        }
    }
