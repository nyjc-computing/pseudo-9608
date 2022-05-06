import unittest

import pseudocode

file = 'procedure.pseudo'

class ProcedureTestCase(unittest.TestCase):
    def setUp(self):
        with open(file) as f:
            src = f.read()
        pseudocode.run(src)
        # Pass src to interpreter
        # Retrieve result: frame, errors, output, etc
        
    def test_procedure(self):
        pass
        