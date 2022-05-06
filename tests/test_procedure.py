import unittest

import pseudocode

file = 'tests/procedure.pseudo'

class ProcedureTestCase(unittest.TestCase):
    def setUp(self):
        with open(file) as f:
            src = f.read()
        self.result = pseudocode.run(src)
        
    def test_procedure(self):
        frame = self.result['frame']
        self.assertIs(
            frame.getType('TestBool'),
            'NULL',
        )
        self.assertIs(
            type(frame.getValue('TestBool')),
            pseudocode.lang.Procedure,
        )
        procedure = frame.getValue('TestBool')
        self.assertTrue(
            procedure.frame.getValue('Succeeded')
        )
        self.assertEqual(
            procedure.frame.getType('Succeeded'),
            'BOOLEAN'
        )