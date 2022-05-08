import unittest

import pseudocode
from tests import capture

TESTCODE = """
PROCEDURE CountDownThenUp(Num : INTEGER)
    OUTPUT Num
    IF Num > 0
      THEN
        OUTPUT CountDown(Num - 1)
    ENDIF
ENDPROCEDURE

CALL CountDownThenUp(10)
"""

class RecursionTestCase(unittest.TestCase):
    def setUp(self):
        pseudo = pseudocode.Pseudo()
        captureOutput, returnOutput = capture('output')
        pseudo.registerHandlers(
            output=captureOutput,
        )
        self.result = pseudo.run(TESTCODE)
        self.result['output'] = returnOutput()
        
    def test_recursion(self):
        # Procedure should complete successfully
        self.assertIsNone(self.result['error'])        

    def test_output(self):
        # Check output
        output = self.result['output']
        self.assertEqual(
            output,
            "10\n9\n8\n7\n6\n5\n4\n3\n2\n1\n0",
        )