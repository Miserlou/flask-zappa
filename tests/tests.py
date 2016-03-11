# -*- coding: utf8 -*-
import base64
import collections
import json
import os
import random
import string
import unittest

from zappa.zappa import Zappa
from flask_zappa.handler import lambda_handler
from bin.client import _init

class TestZappa(unittest.TestCase):

    ##
    # Sanity Tests
    ##

    def test_test(self):
        self.assertTrue(True)
    ##
    # Basic Tests
    ##

    def test_zappa(self):
        self.assertTrue(True)
        Zappa()

    ##
    # Bin settings
    ##

    def test_init(self):
        with open('test_settings.json') as f:
            _init('test', f)


if __name__ == '__main__':
    unittest.main()
