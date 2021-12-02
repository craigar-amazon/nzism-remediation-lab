import unittest

import lib.base as b

r1 = {
    'Runtime': 'python3.8',
    'Handler': 'lambda_function.lambda_handler',
    'Timeout': 600,
    'MemorySize': 128,
    'Environment': {
        'Variables': {
            'LOGLEVEL': 'WARNING'
        }
    },
    'Policy': '{"a": 3, "b": "True", "c": "xyz"}',
    'Capabilities': ['c','a','b']
}

r_role = 'arn-a'
r_description = 'desc-a'

x1 = {
    'Runtime': 'python3.8',
    'Handler': 'lambda_function.lambda_handler',
    'MemorySize': 256,
    'Timeout': 300,
    'Environment': {
        'Variables': {
            'LOGLEVEL': 'WARNING'
        }
    },
    'Policy': '{\n"a":3,\n "b":"True"\n, "c":"xyz"}',
    'Capabilities': ['b','a','c']
}
x_role = 'arn-b'
x_description = 'desc-b'


def normaliseUpper(raw, context):
    return raw.upper()

class TestBase(unittest.TestCase):

    def test_deltabuild(self):
        db = b.DeltaBuild()
        db.updateRequired(r1)
        db.putRequired('Timeout', 500)
        db.putRequired('MemorySize', 256)
        db.putRequired('Environment.Variables.LOGLEVEL', 'ERROR')
        db.putRequired('Environment.Variables.LOGLEVEL', 'INFO')
        db.putRequired('Environment.Variables', {'LOGLEVEL': 'warning'})
        db.loadExisting(x1)
        db.normaliseRequiredJson('Policy')
        db.normaliseRequired('Environment.Variables.LOGLEVEL', lambda raw, context: raw.upper())
        db.normaliseRequiredList('Capabilities')
        db.normaliseExistingJson('Policy')
        db.normaliseExisting('MemorySize', b.normaliseInteger)
        db.normaliseExistingList('Capabilities')
        delta1 = db.delta()
        self.assertTrue('Timeout' in delta1)
        self.assertEqual(len(delta1), 1)
        db.putRequired('Timeout', 300)
        delta2 = db.delta()
        self.assertEqual(len(delta2), 0)


if __name__ == '__main__':
    b.initLogging(None, 'INFO')
    loader = unittest.TestLoader()
    loader.testMethodPrefix = "test_"
    unittest.main(warnings='default', testLoader = loader)
