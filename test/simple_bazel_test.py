"""Tests for simple_bazel."""

import os
from os import path
import subprocess
import unittest

_SCRIPT_FILE = path.join(path.dirname(__file__), '../bin/simple_bazel')


class BazelTestCase(unittest.TestCase):
    """Test the bazel parser."""

    def test_this_repo(self) -> None:
        """It should not fail on the current repo."""

        os.chdir(path.dirname(__file__))
        self.assertTrue(subprocess.check_output(('python', _SCRIPT_FILE), text=True))


if __name__ == '__main__':
    unittest.main()
