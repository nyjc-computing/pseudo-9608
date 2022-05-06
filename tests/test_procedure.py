import unittest

import pseudocode

file = 'tests/procedure.pseudo'

class ProcedureTestCase(unittest.TestCase):
    def setUp(self):
        with open(file) as f:
            src = f.read()
        self.result = pseudocode.run(src)
        
    def test_procedure(self):
        pass
        