#
# Copyright 2015 Carnegie Mellon University
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
from kiloeyes.common import alarm_expr_validator as validator
from kiloeyes.openstack.common import log
from kiloeyes import tests
import os

LOG = log.getLogger(__name__)


class TestCaseUtil(object):
    def __init__(self):
        path = os.path.split(os.path.realpath(__file__))[0]
        path += '/test_case_alarm_expr_validator.json'
        f = open(path)
        try:
            self.test_cases = json.load(f)
        finally:
            f.close()

    def get_alarm_def(self, name):
        return json.dumps(self.test_cases[name])


class TestAlarmExprCalculator(tests.BaseTestCase):
    def setUp(self):
        super(TestAlarmExprCalculator, self).setUp()
        self.util = TestCaseUtil()

    def test_is_valid_alarm_definition(self):
        self.assertEqual(True, validator.is_valid_alarm_definition(
            self.util.get_alarm_def("alarm_def_1")))
        self.assertEqual(True, validator.is_valid_alarm_definition(
            self.util.get_alarm_def("alarm_def_0")))
        self.assertEqual(True, validator.is_valid_alarm_definition(
            self.util.get_alarm_def("alarm_def_1_update")))
        self.assertEqual(True, validator.is_valid_alarm_definition(
            self.util.get_alarm_def("alarm_def_1_update_wrong_0")))
        self.assertEqual(False, validator.is_valid_alarm_definition(
            self.util.get_alarm_def("alarm_def_0_wrong_0")))
        self.assertEqual(False, validator.is_valid_alarm_definition(
            self.util.get_alarm_def("alarm_def_0_wrong_1")))
        self.assertEqual(True, validator.is_valid_alarm_definition(
            self.util.get_alarm_def("alarm_def_1_update_wrong_1")))

    def test_is_valid_update_alarm_definition(self):
        self.assertEqual(True, validator.is_valid_update_alarm_definition(
            self.util.get_alarm_def("alarm_def_1"),
            self.util.get_alarm_def("alarm_def_1_update")))
        self.assertEqual(False, validator.is_valid_update_alarm_definition(
            self.util.get_alarm_def("alarm_def_1"),
            self.util.get_alarm_def("alarm_def_0_wrong_0")))
        self.assertEqual(False, validator.is_valid_update_alarm_definition(
            self.util.get_alarm_def("alarm_def_1"),
            self.util.get_alarm_def("alarm_def_1_update_wrong_0")))
        self.assertEqual(False, validator.is_valid_update_alarm_definition(
            self.util.get_alarm_def("alarm_def_1"),
            self.util.get_alarm_def("alarm_def_1_update_wrong_1")))
        self.assertEqual(False, validator.is_valid_update_alarm_definition(
            self.util.get_alarm_def("alarm_def_1"),
            self.util.get_alarm_def("alarm_def_1_update_wrong_2")))
        self.assertEqual(False, validator.is_valid_update_alarm_definition(
            self.util.get_alarm_def("alarm_def_1"),
            self.util.get_alarm_def("alarm_def_1_update_wrong_3")))
