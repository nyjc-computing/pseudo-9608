import unittest

import pseudocode
from tests import capture

file = 'tests/procedure.pseudo'

class ProcedureTestCase(unittest.TestCase):
    def setUp(self):
        pseudo = pseudocode.Pseudo()
        captureOutput, returnOutput = capture('output')
        pseudo.registerHandlers(
            output=captureOutput,
        )
        with open(file) as f:
            src = f.read()
        self.result = pseudo.run(src)
        self.result['output'] = returnOutput()
        
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

    def test_output(self):
        output = self.result['output']
        self.assertEqual(output, "Awww!\n")