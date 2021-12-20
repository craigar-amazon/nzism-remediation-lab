import unittest

from lib.base import initLogging
from lib.base.request import DispatchEvent, DispatchEventTarget

import lib.lambdas.core.cwdims as cwdims

class TestBase(unittest.TestCase):

    def test_basic(self):
        t = {}
        t['awsAccountName'] = 'a1'
        t['awsRegion'] = 'r1'
        t['resourceType'] = 't1'

        artags = {
            'AutoDeployed': 'True',
            'AutoDeploymentReason': 'NZISM Conformance',
            'NZISM': 'CID:3548+CID:3562+CID:4838'
        }

        e = {}
        e['action'] = 'remediate'
        e['configRuleName'] = 'c1'
        e['autoResourceTags'] = artags

        dimListA = [
            'ConfigRule/Account/Region',
            'ConfigRule',
            'Account',
            'AutoResourceTag.NZISM/Account',
            'Bogus',
            'AutoResourceTag.ACSC/ResourceType'
        ]

        target = DispatchEventTarget(t)
        event = DispatchEvent(e, target)

        dmsA = cwdims.get_dimension_maps(event, dimListA)
        self.assertEqual(len(dmsA), 8)
        self.assertEqual(dmsA[0].get('ConfigRule'), 'c1')
        self.assertEqual(dmsA[0].get('AccountName'), 'a1')
        self.assertEqual(dmsA[0].get('Region'), 'r1')
        self.assertEqual(dmsA[1].get('ConfigRule'), 'c1')
        self.assertEqual(dmsA[2].get('AccountName'), 'a1')
        self.assertEqual(dmsA[3].get('NZISM'), 'CID:3548')
        self.assertEqual(dmsA[3].get('AccountName'), 'a1')
        self.assertEqual(dmsA[4].get('NZISM'), 'CID:3562')
        self.assertEqual(dmsA[4].get('AccountName'), 'a1')
        self.assertEqual(dmsA[5].get('NZISM'), 'CID:4838')
        self.assertEqual(dmsA[5].get('AccountName'), 'a1')
        self.assertEqual(dmsA[6].get('Bogus'), 'Unspecified')
        self.assertEqual(dmsA[7].get('ACSC'), 'Unspecified')
        self.assertEqual(dmsA[7].get('ResourceType'), 't1')

        dimListB = 'ResourceType'
        dmsB = cwdims.get_dimension_maps(event, dimListB)
        self.assertEqual(len(dmsB), 1)
        self.assertEqual(dmsB[0].get('ResourceType'), 't1')


    def test_theory(self):
        t = {}
        t['awsAccountName'] = 'a1'
        t['awsRegion'] = 'r1'
        t['resourceType'] = 't1'

        artags = {
            'AutoDeployed': 'True',
            'AutoDeploymentReason': 'NZISM Conformance',
            'X': 'x2+x4+x6',
            'Y': 'y3',
            'Z': 'z5+z7'
        }

        e = {}
        e['action'] = 'remediate'
        e['configRuleName'] = 'c1'
        e['autoResourceTags'] = artags

        dimListA = [
            'AutoResourceTag.X/AutoResourceTag.Y/AutoResourceTag.Z'
        ]

        target = DispatchEventTarget(t)
        event = DispatchEvent(e, target)

        dmsA = cwdims.get_dimension_maps(event, dimListA)
        self.assertEqual(len(dmsA), 6)
        self.assertEqual(dmsA[0].get('X'), 'x2')
        self.assertEqual(dmsA[0].get('Y'), 'y3')
        self.assertEqual(dmsA[0].get('Z'), 'z5')
        self.assertEqual(dmsA[1].get('X'), 'x2')
        self.assertEqual(dmsA[1].get('Y'), 'y3')
        self.assertEqual(dmsA[1].get('Z'), 'z7')
        self.assertEqual(dmsA[2].get('X'), 'x4')
        self.assertEqual(dmsA[2].get('Y'), 'y3')
        self.assertEqual(dmsA[2].get('Z'), 'z5')
        self.assertEqual(dmsA[3].get('X'), 'x4')
        self.assertEqual(dmsA[3].get('Y'), 'y3')
        self.assertEqual(dmsA[3].get('Z'), 'z7')
        self.assertEqual(dmsA[4].get('X'), 'x6')
        self.assertEqual(dmsA[4].get('Y'), 'y3')
        self.assertEqual(dmsA[4].get('Z'), 'z5')
        self.assertEqual(dmsA[5].get('X'), 'x6')
        self.assertEqual(dmsA[5].get('Y'), 'y3')
        self.assertEqual(dmsA[5].get('Z'), 'z7')


if __name__ == '__main__':
    initLogging(None, 'INFO')
    loader = unittest.TestLoader()
    loader.testMethodPrefix = "test_"
    unittest.main(warnings='default', testLoader = loader)
