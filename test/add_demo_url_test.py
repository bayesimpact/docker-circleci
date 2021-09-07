"""Tests for the add_demo_url script."""

import json
import os
from os import path
import subprocess
import time
import unittest

_SCRIPT_NAME = path.basename(__file__).removesuffix('_test.py')
_SCRIPT_PATH = f'{path.dirname(path.dirname(path.abspath(__file__)))}/bin/{_SCRIPT_NAME}'

_DEFAULT_FILE = '/tmp/demo_urls.json'
_DEFAULT_REPLACEMENT = f'/tmp/demo_urls_{int(time.time()):d}.json'


class AddDemoUrlsTestCase(unittest.TestCase):
    """Classic tests for the script."""

    def setUp(self) -> None:
        super().setUp()
        if path.exists(_DEFAULT_FILE):
            os.rename(_DEFAULT_FILE, _DEFAULT_REPLACEMENT)

    def tearDown(self) -> None:
        super().tearDown()
        if path.exists(_DEFAULT_REPLACEMENT):
            os.rename(_DEFAULT_REPLACEMENT, _DEFAULT_FILE)
            return
        if path.exists(_DEFAULT_FILE):
            os.remove(_DEFAULT_FILE)

    def _run_script(self, *args: str) -> str:
        return subprocess.check_output((_SCRIPT_PATH, *args), text=True, stderr=subprocess.STDOUT)

    def test_no_args(self) -> None:
        """Running with no args returns an error."""

        with self.assertRaises(subprocess.CalledProcessError) as cpe:
            self._run_script()
        err = cpe.exception.stdout
        self.assertIn('required: name, url', err)

    def test_name_only(self) -> None:
        """Running with a name only returns an error."""

        with self.assertRaises(subprocess.CalledProcessError) as cpe:
            self._run_script('client')
        err = cpe.exception.stdout
        self.assertIn('required: url', err)

    def test_with_url(self) -> None:
        """Running with a name and a URL works."""

        self.assertFalse(path.exists(_DEFAULT_FILE))
        self._run_script('client', 'https://www.google.fr')
        self.assertTrue(path.exists(_DEFAULT_FILE))
        with open(_DEFAULT_FILE, 'r') as file:
            self.assertEqual({'client': 'https://www.google.fr'}, json.load(file))

    def test_with_existing_file(self) -> None:
        """Runnin with an already existing file works."""

        self._run_script('client', 'https://www.google.fr')
        self._run_script('server', 'https://www.facebook.com')
        self.assertTrue(path.exists(_DEFAULT_FILE))
        with open(_DEFAULT_FILE, 'r') as file:
            self.assertEqual({
                'client': 'https://www.google.fr',
                'server': 'https://www.facebook.com',
            }, json.load(file))

    def test_with_non_default_file(self) -> None:
        """Works with a specified file."""

        tempfile = f'/tmp/temp_test_{int(time.time()):d}.json'
        self._run_script('client', 'https://www.google.fr', '--file', tempfile)
        with open(tempfile, 'r') as file:
            self.assertEqual({'client': 'https://www.google.fr'}, json.load(file))
        self._run_script('server', 'https://www.facebook.com', '--file', tempfile)
        with open(tempfile, 'r') as file:
            self.assertEqual({
                'client': 'https://www.google.fr',
                'server': 'https://www.facebook.com',
            }, json.load(file))
        os.remove(tempfile)


if __name__ == '__main__':
    unittest.main()
