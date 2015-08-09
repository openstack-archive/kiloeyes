# Copyright 2013 IBM Corp
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
import mock
from oslo_config import fixture
from oslo_log import log
import requests

from kiloeyes.common import es_conn
from kiloeyes.microservice import timed_strategy
from kiloeyes import tests

LOG = log.getLogger(__name__)


class TestESConnection(tests.BaseTestCase):

    def setUp(self):
        super(TestESConnection, self).setUp()
        self.CONF = self.useFixture(fixture.Config()).conf

    def test_send_messages_with_id(self):
        self.CONF.set_override('id_field', 'id', group='es_conn')
        self.CONF.set_override('uri', 'http://fake', group='es_conn')
        self.CONF.set_override('time_unit', 'h', group='timed_strategy')
        strategy = timed_strategy.TimedStrategy()
        conn = es_conn.ESConnection('alarms', strategy, 'pre_')
        req_result = mock.Mock()
        req_result.status_code = 204
        msg = {'id': 'whatever'}
        with mock.patch.object(requests, 'post', return_value=req_result):
            conn.send_messages(json.dumps(msg))
            self.assertTrue(requests.post.called)

    def test_send_messages_without_id(self):
        self.CONF.set_override('id_field', 'id', group='es_conn')
        self.CONF.set_override('uri', 'http://fake', group='es_conn')
        self.CONF.set_override('time_unit', 'h', group='timed_strategy')
        strategy = timed_strategy.TimedStrategy()
        conn = es_conn.ESConnection('alarms', strategy, 'pre_')
        req_result = mock.Mock()
        req_result.status_code = 204
        msg = {'not_id': 'whatever'}
        with mock.patch.object(requests, 'post', return_value=req_result):
            res = conn.send_messages(json.dumps(msg))
            self.assertFalse(requests.post.called)
            self.assertEqual(res, 400)
