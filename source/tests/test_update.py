# -*- coding: utf-8 -*-
import unittest

from app.update import UpdateError, is_newer


class UpdateVersionTests(unittest.TestCase):
    def test_newer_semantic_version_is_detected(self):
        self.assertTrue(is_newer("v0.2.1", "0.2.0"))
        self.assertTrue(is_newer("1.0", "0.9.99"))
        self.assertFalse(is_newer("0.2.0", "0.2.0"))
        self.assertFalse(is_newer("0.1.9", "0.2.0"))

    def test_invalid_version_is_rejected(self):
        with self.assertRaises(UpdateError):
            is_newer("latest", "0.2.0")
