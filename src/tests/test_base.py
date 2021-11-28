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
    'Policy': '{"a": 3, "b": "True", "c": "xyz"}'
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
    'Policy': '{\n"a":3,\n "b":"True"\n, "c":"xyz"}'
}
x_role = 'arn-b'
x_description = 'desc-b'


def normaliseUpper(raw, context):
    return raw.upper()

class TestBase(unittest.TestCase):

    def test_deltabuild(self):
        db = b.DeltaBuild()
        db.updateRequired(r1)
        db.putRequired(500, 'Timeout')
        db.putRequired(256, 'MemorySize')
        db.putRequired('ERROR', 'Environment', 'Variables', 'LOGLEVEL')
        db.putRequired('INFO', 'Environment.Variables.LOGLEVEL')
        db.putRequired({'LOGLEVEL': 'warning'}, 'Environment', 'Variables')
        db.loadExisting(x1)
        db.normaliseRequiredJson('Policy')
        db.normaliseRequired(lambda raw, context: raw.upper(), 'Environment', 'Variables', 'LOGLEVEL')
        db.normaliseExistingJson('Policy')
        db.normaliseExisting(b.normaliseInteger, 'MemorySize')
        delta1 = db.delta()
        self.assertTrue('Timeout' in delta1)
        db.putRequired(300, 'Timeout')
        delta2 = db.delta()
        self.assertEquals(len(delta2), 0)


if __name__ == '__main__':
    b.initLogging(None, 'INFO')
    loader = unittest.TestLoader()
    loader.testMethodPrefix = "test_"
    unittest.main(warnings='default', testLoader = loader)
