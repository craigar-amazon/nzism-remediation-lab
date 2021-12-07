import unittest
from lib.base import initLogging
from lib.rdq import RdqError

from lambdas.test.EncryptCWL.lambda_function import lambda_handler

import tests.util_lambda as util

def _isPreview():
    return False

def _setupHandler(profile, resourceId):
    return
    # s3c = S3ControlClient(profile)
    # s3c.declarePublicAccessBlock(resourceId, False)

def _configRuleName():
    return 'cloudwatch-log-group-encrypted'

def _resourceType():
    return 'AWS::Logs::LogGroup'

def _codeFolder():
    return 'EncryptCWL'

class TestRule(unittest.TestCase):
    def test_setup(self):
        util.show_reminder_targetApplication()
        util.setup_targetAccount()

    def test_local(self):
        util.show_reminder_dispatchingAudit()
        resourceId = '/aws/lambda/UnitTest1Lambda'
        try:
            response = util.run_local(_isPreview(), _configRuleName(), _resourceType(), resourceId, _setupHandler, lambda_handler)
            print(response)
            self.assertTrue(response)
        except RdqError as e:
            self.fail(e)

    def test_direct(self):
        util.show_reminder_dispatchingAudit()
        resourceId = util.targetAccountId()
        try:
            response = util.run_direct(_isPreview(), _configRuleName(), _resourceType(), resourceId, _setupHandler, lambda_handler)
            print(response)
            self.assertTrue(response)
        except RdqError as e:
            self.fail(e)

    def test_invoke(self):
        util.show_reminder_dispatchingAudit()
        resourceId = util.targetAccountId()
        try:
            response = util.run_invoke(_isPreview(), _configRuleName(), _resourceType(), resourceId, _setupHandler, _codeFolder())
            print("Lambda Response: {}".format(response))
            self.assertTrue(response)
        except RdqError as e:
            self.fail(e)

if __name__ == '__main__':
    initLogging(None, 'INFO')
    loader = unittest.TestLoader()
    loader.testMethodPrefix = "test_local"
    unittest.main(warnings='default', testLoader = loader)
