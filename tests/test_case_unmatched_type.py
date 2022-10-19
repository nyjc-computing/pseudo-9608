import unittest

import pseudocode

TESTCODE = """
DECLARE Test : STRING

Test <- "Hi"

CASE OF Test
  "Hello": OUTPUT "Oh, hello there!"
  "Hi": OUTPUT "Hi again!"
  "Yo": OUTPUT "Wassup?"
  0: OUTPUT "Huh?"
  1: OUTPUT "No way..."
ENDCASE
"""

class ProcedureTestCase(unittest.TestCase):
    def setUp(self):
        pseudo = pseudocode.Pseudo()
        self.result = pseudo.run(TESTCODE)
        
    def test_error(self):
        # Procedure should NOT complete successfully
        error = self.result['error']
        self.assertTrue(
            issubclass(
                type(error),
                pseudocode.builtin.PseudoError,
            )
        )
        self.assertIs(
            type(error),
            pseudocode.builtin.LogicError,
        )
        infoword = 'expect'
        self.assertIn(
            infoword,
            error.msg().lower(),
            f"Error message does not contain {infoword!r}"
        )
