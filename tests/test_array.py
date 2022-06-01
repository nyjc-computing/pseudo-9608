import unittest

import pseudocode
from tests import capture

TESTCODE = """
DECLARE AnArray : ARRAY[1:10] OF INTEGER
TYPE Student
    DECLARE Surname : STRING
    DECLARE FirstName : STRING
    DECLARE YearGroup : INTEGER
ENDTYPE
DECLARE Pupil1 : Student
DECLARE Var : INTEGER

FOR Var <- 1 TO 10
    AnArray[Var] <- Var
ENDFOR
Pupil1.Surname <- "Johnson"
Pupil1.FirstName <- "Leroy"
Pupil1.YearGroup <- 6
Var <- 9
OUTPUT Pupil1.Surname
OUTPUT Pupil1.FirstName
OUTPUT Pupil1.YearGroup
FOR Var <- 1 TO 10
    OUTPUT AnArray[Var]
ENDFOR
"""

EXPECTED = "Johnson\nLeroy\n6\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n"

class ProcedureTestCase(unittest.TestCase):
    def setUp(self):
        pseudo = pseudocode.Pseudo()
        captureOutput, returnOutput = capture('output')
        pseudo.registerHandlers(
            output=captureOutput,
        )
        self.result = pseudo.run(TESTCODE)
        self.result['output'] = returnOutput()
        
    def test_array(self):
        # Procedure should complete successfully
        self.assertIsNone(self.result['error'])
        
        frame = self.result['frame']

        # Check procedure type
        self.assertIs(
            frame.getType('AnArray'),
            'ARRAY',
        )
        self.assertIs(
            type(frame.getValue('AnArray')),
            pseudocode.lang.Array,
        )
        
        array = frame.getValue('AnArray')

        # Check procedure params
        self.assertEqual(
            array.elementType,
            'INTEGER'
        )

    def test_output(self):
        # Check output
        output = self.result['output']
        self.assertEqual(output, EXPECTED)