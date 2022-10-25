import unittest

import pseudocode
from tests import capture

TESTCODE = """
DECLARE Length : INTEGER
DECLARE Data : ARRAY[1:10] OF INTEGER
DECLARE i : INTEGER

Length <- 10

PROCEDURE BubbleSort(BYREF Data: ARRAY[1:10] OF INTEGER, Length: INTEGER)
    DECLARE i : INTEGER
    DECLARE j : INTEGER
    DECLARE Temp : INTEGER

    FOR i <- 1 TO Length - 1
        FOR j <- 1 TO Length - i
            IF Data[j] > Data[j + 1]
              THEN
                Temp <- Data[j]
                Data[j] <- Data[j + 1]
                Data[j + 1] <- Temp
            ENDIF
        ENDFOR
    ENDFOR
ENDPROCEDURE

Data[1] <- 7
Data[2] <- 9
Data[3] <- 4
Data[4] <- 1
Data[5] <- 2
Data[6] <- 3
Data[7] <- 5
Data[8] <- 10
Data[9] <- 6
Data[10] <- 8

CALL BubbleSort(Data, Length)

FOR i <- 1 TO 10
    OUTPUT Data[i]
ENDFOR
"""

EXPECTED = "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n"

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
        
        frame = self.result['env'].frame

        # Check procedure type
        self.assertEqual(
            frame.getType('BubbleSort'),
            'NULL',
        )
        self.assertIs(
            type(frame.getValue('BubbleSort')),
            pseudocode.lang.Procedure,
        )
        
        procedure = frame.getValue('BubbleSort')

    def test_output(self):
        # Check output
        output = self.result['output']
        self.assertEqual(output, EXPECTED)
