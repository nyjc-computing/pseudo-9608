import unittest

import pseudocode
from tests import capture

TESTCODE = """
PROCEDURE TestBool(Succeeded : BOOLEAN)
    IF Succeeded = TRUE AND NOT (-1.2 = -1.5)
      THEN
        OUTPUT "Yay!"
      ELSE
        OUTPUT "Awww!"
    ENDIF
ENDPROCEDURE

CALL TestBool(TRUE)
"""

class ProcedureTestCase(unittest.TestCase):
    def setUp(self):
        pseudo = pseudocode.Pseudo()
        captureOutput, returnOutput = capture('output')
        pseudo.registerHandlers(
            output=captureOutput,
        )
        self.result = pseudo.run(TESTCODE)
        self.result['output'] = returnOutput()
        
    def test_procedure(self):
        # Procedure should complete successfully
        self.assertIsNone(self.result['error'])
        
        frame = self.result['frame']

        # Check procedure type
        self.assertIs(
            frame.getType('TestBool'),
            'NULL',
        )
        self.assertIs(
            type(frame.getValue('TestBool')),
            pseudocode.lang.Procedure,
        )
        
        procedure = frame.getValue('TestBool')

        # Check procedure params
        self.assertTrue(
            procedure.frame.getValue('Succeeded')
        )
        self.assertEqual(
            procedure.frame.getType('Succeeded'),
            'BOOLEAN'
        )

    def test_output(self):
        # Check output
        output = self.result['output']
        self.assertEqual(output, "Yay!\n")