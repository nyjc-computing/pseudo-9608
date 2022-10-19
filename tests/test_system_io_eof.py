import unittest

import os

import pseudocode
from tests import capture

TESTFILE = "testfile.txt"

TESTCODE = (
    f'OPENFILE "{TESTFILE}" FOR READ\n'
    f'OUTPUT EOF("{TESTFILE}")\n'
    f'CLOSEFILE "{TESTFILE}"'
)

class SystemTestCase(unittest.TestCase):
    def setUp(self):
        with open(TESTFILE, "w") as file:
            self.filename = file.name
            for i in range(10):
                file.write(f"{i}\n")
        pseudo = pseudocode.Pseudo()
        captureOutput, returnOutput = capture('output')
        pseudo.registerHandlers(
            output=captureOutput,
        )
        self.result = pseudo.run(TESTCODE)
        self.result['output'] = returnOutput()
        
    def test_system(self):
        # Procedure should complete successfully
        self.assertIsNone(self.result['error'])        

    def test_output(self):
        # Check output
        output = self.result['output']
        self.assertEqual(
            output.strip(), 'FALSE',
        )

    def tearDown(self):
        os.remove(TESTFILE)
