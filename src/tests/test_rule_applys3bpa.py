import unittest
from lib.base import initLogging
from lib.rdq import RdqError
from lib.rdq.svcs3control import S3ControlClient
from lambdas.test.ApplyS3BPA.lambda_function import lambda_handler

import tests.util_lambda as util

def _isPreview():
    return False

def _setupHandler(profile, resourceId):
    s3c = S3ControlClient(profile)
    s3c.declarePublicAccessBlock(resourceId, False)

def _configRuleName():
    return 's3-account-level-public-access-blocks-periodic'

def _resourceType():
    return 'AWS::::Account'

def _codeFolder():
    return 'ApplyS3BPA'

class TestRule(unittest.TestCase):
    def test_setup(self):
        print("ACTION: Ensure credentials set to target application account")
        util.setup_targetAccount()

    def test_local(self):
        print("ACTION: Ensure credentials set to dispatching audit account")
        resourceId = util.dispatchAccountId()
        try:
            response = util.run_local(_isPreview(), _configRuleName(), _resourceType(), resourceId, _setupHandler, lambda_handler)
            print(response)
            self.assertTrue(response)
        except RdqError as e:
            self.fail(e)

    def test_direct(self):
        print("ACTION: Ensure credentials set to dispatching audit account")
        resourceId = util.targetAccountId()
        try:
            response = util.run_direct(_isPreview(), _configRuleName(), _resourceType(), resourceId, _setupHandler, lambda_handler)
            print(response)
            self.assertTrue(response)
        except RdqError as e:
            self.fail(e)

    def test_invoke(self):
        print("ACTION: Ensure credentials set to dispatching audit account")
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
    loader.testMethodPrefix = "test_invoke"
    unittest.main(warnings='default', testLoader = loader)
