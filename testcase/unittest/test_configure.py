#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2017 theloop Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test Configure class"""

import logging
import sys
import unittest
from pathlib import Path

import loopchain.utils as util
import testcase.unittest.test_util as test_util

sys.path.append('../')
from loopchain import configure as conf
from loopchain import configure_default as conf_default

util.set_log_level_debug()


class TestConfigure(unittest.TestCase):

    def setUp(self):
        test_util.print_testname(self._testMethodName)

    def tearDown(self):
        util.set_log_level_debug()

    def test_get_configure(self):
        logging.debug(f"conf.IP_LOCAL: {conf.IP_LOCAL}")
        self.assertEqual(conf.IP_LOCAL, conf_default.IP_LOCAL)

        logging.debug(f"conf.GRPC_TIMEOUT: {conf.GRPC_TIMEOUT}")
        self.assertTrue(isinstance(conf.GRPC_TIMEOUT, int))

        logging.debug(f"conf.LOG_LEVEL: {conf.LOG_LEVEL}")
        self.assertEqual(conf.LOG_LEVEL, conf_default.LOG_LEVEL)

        logging.debug(f"conf.LEVEL_DB_KEY_FOR_PEER_LIST: {conf.LEVEL_DB_KEY_FOR_PEER_LIST}")
        self.assertEqual(conf.LEVEL_DB_KEY_FOR_PEER_LIST, conf_default.LEVEL_DB_KEY_FOR_PEER_LIST)

        logging.debug(f"conf.TOKEN_TYPE_TOKEN: {conf.TOKEN_TYPE_TOKEN}")
        self.assertTrue(isinstance(conf.TOKEN_TYPE_TOKEN, str))

    def test_load_configure_json(self):
        # GIVEN
        ip_local_before_load_json = conf.IP_LOCAL
        token_type_token_before_load_json = conf_default.TOKEN_TYPE_TOKEN
        logging.debug(f"before json file load, conf.IP_LOCAL({ip_local_before_load_json})"
                      f", conf.TOKEN_TYPE_TOKEN({token_type_token_before_load_json})")

        test_configure_json_path = "configure_json_for_test.json"
        configure_json_file = Path(test_configure_json_path)
        if not configure_json_file.is_file():
            test_configure_json_path = "testcase/unittest/configure_json_for_test.json"

        # WHEN
        conf.Configure().load_configure_json(test_configure_json_path)
        logging.debug(f"after json file load, conf.IP_LOCAL({conf.IP_LOCAL})"
                      f", conf.TOKEN_TYPE_TOKEN({conf.TOKEN_TYPE_TOKEN})")

        # THEN
        self.assertNotEqual(ip_local_before_load_json, conf.IP_LOCAL)
        self.assertNotEqual(token_type_token_before_load_json, conf.TOKEN_TYPE_TOKEN)

        # BACK
        conf.IP_LOCAL = ip_local_before_load_json
        conf.TOKEN_TYPE_TOKEN = token_type_token_before_load_json


if __name__ == '__main__':
    unittest.main()
