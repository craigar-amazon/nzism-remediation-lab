import unittest

import lib.base as b


def normaliseUpper(raw, context):
    return raw.upper()

class TestBase(unittest.TestCase):

    def test_tags(self):
        t1 = b.Tags()
        t1.putAll(Compliance="NZISM", AutoRemediated=True)
        t1.put('Classification', "Sensitive")
        t2 = b.Tags()
        t2.put('Project', "Blueprints")
        t1.update(t2)
        t3 = b.Tags()
        t3.putAll(Compliance="NIST", AutoRemediated=True)
        t4 = b.Tags()
        t4.putAll(Compliance="NZISM", AutoRemediated=True, Project="Blueprints", Classification="Sensitive")
        t5 = b.Tags()
        t5.putAll(Compliance="NIST", AutoRemediated=True)
        d4 = b.Tags()
        d4.update({
            'Compliance':"NZISM",
            'Project': "Blueprints",
            'AutoRemediated': True,
            'Classification': "Sensitive"    
        })
        l4 = b.Tags()
        l4.update([
            {'Key': 'AutoRemediated', 'Value': True},
            {'Key': 'Classification', 'Value': 'Sensitive'},
            {'Key': 'Project', 'Value': 'Blueprints'},
            {'Key': 'Compliance', 'Value': 'NZISM'},
        ])
        l5 = b.Tags()
        l5.update([
            {'Key': 'AutoRemediated', 'Value': False},
            {'Key': 'Classification', 'Value': 'Sensitive'},
            {'Key': 'Project', 'Value': 'Blueprints'},
            {'Key': 'Compliance', 'Value': 'NZISM'},
        ])
        l6 = b.Tags()
        l6.update([
            {'Key': 'AutoRemediated', 'Value': False},
            {'Key': 'Classification', 'Value': 'Sensitive'},
            {'Key': 'Lifecycle', 'Value': 'Dev'},
            {'Key': 'Compliance', 'Value': 'NZISM'},
        ])
        self.assertFalse(t1 == t2)
        self.assertTrue(t1 == t4)
        self.assertTrue(t1 == d4)
        self.assertTrue(t1 == l4)
        self.assertFalse(t1 == l5)
        self.assertFalse(t1 == l6)
        self.assertTrue(t3 == t5)

        l4l5 = l4.subtract(l5)
        self.assertEqual(l4l5.get('AutoRemediated'), 'True')
        l5l6 = l5.subtract(l6)
        self.assertEqual(l5l6.get('Project'), 'Blueprints')
        self.assertIsNone(l5l6.get('Lifecycle'))

    def test_deltabuild(self):
        t1 = b.Tags()
        t1.putAll(Compliance="NZISM", AutoRemediated=True, Classification="Sensitive")
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
            'Capabilities': ['c','a','b'],
        }

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
            'Capabilities': ['b','a','c'],
            'TagsD': {
                'Compliance': "NZISM",
                'AutoRemediated': 'True',
                'Classification': "Sensitive"
            },
            'TagsL': [
                {'Key': 'Compliance', 'Value': "NZISM"},
                {'Key': 'AutoRemediated', 'Value': "True"},
                {'Key': 'Classification', 'Value': "Sensitive"}
            ]
        }
        db = b.DeltaBuild()
        db.updateRequired(r1)
        db.putRequired('Timeout', 500)
        db.putRequired('MemorySize', 256)
        db.putRequired('Environment.Variables.LOGLEVEL', 'ERROR')
        db.putRequired('Environment.Variables.LOGLEVEL', 'INFO')
        db.putRequired('Environment.Variables', {'LOGLEVEL': 'warning'})
        db.putRequired("TagsL", t1)
        db.putRequired("TagsD", t1)
        db.loadExisting(x1)
        db.normaliseRequiredJson('Policy')
        db.normaliseRequired('Environment.Variables.LOGLEVEL', lambda raw, context: raw.upper())
        db.normaliseRequiredList('Capabilities')
        db.normaliseExistingJson('Policy')
        db.normaliseExisting('MemorySize', b.normaliseInteger)
        db.normaliseExistingList('Capabilities')
        db.normaliseExistingTags("TagsL")
        db.normaliseExistingTags("TagsD")
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
