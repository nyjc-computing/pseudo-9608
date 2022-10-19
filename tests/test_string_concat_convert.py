import unittest

import pseudocode
from tests import capture

TESTCODE = """
OUTPUT "A: " & INTTOSTRING(1) & ", B: " & INTTOSTRING(999)
"""

EXPECTED = "A: 1, B: 999\n"

class ProcedureTestCase(unittest.TestCase):
    def setUp(self):
        pseudo = pseudocode.Pseudo()
        captureOutput, returnOutput = capture('output')
        pseudo.registerHandlers(
            output=captureOutput,
        )
        self.result = pseudo.run(TESTCODE)
        self.result['output'] = returnOutput()
        
    def test_string(self):
        # Code should complete successfully
        self.assertIsNone(self.result['error'])        

    def test_output(self):
        # Check output
        output = self.result['output']
        self.assertEqual(output, EXPECTED)
