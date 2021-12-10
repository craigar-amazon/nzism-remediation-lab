import logging
import json
import unittest
from lib.base import initLogging
from lib.rdq import RdqError

from lambdas.test.EncryptCWL.lambda_function import lambda_handler

import tests.util_lambda as util

_configRuleName = 'cloudwatch-log-group-encrypted'
_resourceType = 'AWS::Logs::LogGroup'
_codeFolder = 'EncryptCWL'

_isPreview = False
_action = 'remediate'

def _setupHandler(profile, resourceId):
    return
    # s3c = S3ControlClient(profile)
    # s3c.declarePublicAccessBlock(resourceId, False)

class TestRule(unittest.TestCase):
    def test_setup(self):
        util.show_reminder_targetApplication()
        util.setup_targetAccount()

    def test_local(self):
        util.show_reminder_dispatchingAudit()
        preview = False
        resourceId = '/aws/lambda/UnitTest1Lambda'
        action = 'baseline'
        deploymentMethod = {'CreateStack': False, 'StackMaxSecs': 300}
        try:
            response = util.run_local(preview, _configRuleName, _resourceType, resourceId, action, deploymentMethod, _setupHandler, lambda_handler)
            logging.info("%s", json.dumps(response))
            self.assertTrue(response)
        except Exception as e:
            self.fail(e)

    def test_direct(self):
        util.show_reminder_dispatchingAudit()
        resourceId = '/aws/lambda/UnitTest1Lambda'
        deploymentMethod = {'CreateStack': True, 'StackMaxSecs': 300}
        try:
            response = util.run_direct(_isPreview, _configRuleName, _resourceType, resourceId, _action, deploymentMethod, _setupHandler, lambda_handler)
            print(response)
            self.assertTrue(response)
        except Exception as e:
            self.fail(e)

    def test_invoke(self):
        util.show_reminder_dispatchingAudit()
        resourceId = '/aws/lambda/UnitTest1Lambda'
        deploymentMethod = {'CreateStack': True, 'StackMaxSecs': 300}
        try:
            response = util.run_invoke(_isPreview, _configRuleName, _resourceType, resourceId, _action, deploymentMethod, _setupHandler, _codeFolder())
            print("Lambda Response: {}".format(response))
            self.assertTrue(response)
        except Exception as e:
            self.fail(e)

if __name__ == '__main__':
    initLogging(None, 'INFO')
    loader = unittest.TestLoader()
    loader.testMethodPrefix = "test_local"
    unittest.main(warnings='default', testLoader = loader)
