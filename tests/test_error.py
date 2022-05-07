import unittest

import pseudocode

TESTCODE = """
IF TRUE
"""

class ProcedureTestCase(unittest.TestCase):
    def setUp(self):
        pseudo = pseudocode.Pseudo()
        self.result = pseudo.run(TESTCODE)
        
    def test_error(self):
        # Procedure should complete successfully
        error = self.result['error']
        self.assertTrue(
            issubclass(
                type(error),
                pseudocode.builtin.PseudoError,
            )
        )
        self.assertIs(
            type(error),
            pseudocode.builtin.ParseError,
        )
