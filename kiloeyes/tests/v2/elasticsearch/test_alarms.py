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

import falcon
import mock
import os
from oslo_config import fixture as fixture_config
from oslotest import base

from kiloeyes.common import es_conn
from kiloeyes.v2.elasticsearch import alarms

try:
    import ujson as json
except ImportError:
    import json


class TestAlarmDispatcher(base.BaseTestCase):

    def setUp(self):
        self.CONF = self.useFixture(fixture_config.Config()).conf
        self.CONF.set_override('doc_type', 'fake', group='alarms')
        self.CONF.set_override('uri', 'fake_es_uri', group='es_conn')
        super(TestAlarmDispatcher, self).setUp()

        self.dispatcher_get = (
            alarms.AlarmDispatcher({}))

        self.dispatcher_get_by_id = (
            alarms.AlarmDispatcher({}))

        self.dispatcher_put = (
            alarms.AlarmDispatcher({}))

        self.dispatcher_delete = (
            alarms.AlarmDispatcher({}))

        dir_path = os.path.dirname(os.path.realpath(__file__))
        alarms_data_json = open(os.path.join(dir_path,
                                             'test_alarms_data')
                                ).read().replace('\n', '')
        self.data = json.loads(alarms_data_json)
        get_alarms_data = open(os.path.join(dir_path,
                                            'test_get_alarms_data')
                               ).read().replace('\n', '')
        self.get_alarms_data = json.loads(get_alarms_data)

    def test_initialization(self):
        # test that the doc type of the es connection is fake
        self.assertEqual(self.dispatcher_get._es_conn.doc_type, 'fake')

        self.assertEqual(self.dispatcher_get._es_conn.uri, 'fake_es_uri/')

    def test_do_get_alarms(self):
        res = mock.Mock()
        req = mock.Mock()
        req_result = mock.Mock()
        response_str = self.get_alarms_data
        req_result.json.return_value = response_str
        req_result.status_code = 200

        req.query_string = 'metric_dimensions=hostname:h7,os:linux&state=OK'
        with mock.patch.object(es_conn.ESConnection, 'get_messages',
                               return_value=req_result):
            self.dispatcher_get.do_get_alarms(req, res)

        # test that the response code is 200
        self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))
        json_result = json.loads(res.body)
        obj = json_result['elements']

        # test that the first response object has the required properties
        self.assertEqual(obj[0]['id'],
                         '1bcbe772-f12b-44ef-a1b5-7685baeaaba2')
        self.assertIsNotNone(obj[0]['alarm_definition'])
        self.assertIsNotNone(obj[0]['metrics'])
        self.assertEqual(obj[0]['state'], 'OK')
        self.assertIsNotNone(obj[0]['sub_alarms'])

        # test that the second response object has the required properties
        self.assertEqual(obj[1]['id'],
                         '256acdac-2f05-4e3e-85a3-802055bf2863')
        self.assertIsNotNone(obj[1]['alarm_definition'])
        self.assertIsNotNone(obj[1]['metrics'])
        self.assertEqual(obj[1]['state'], 'UNDETERMINED')
        self.assertIsNotNone(obj[1]['sub_alarms'])
        self.assertEqual(len(obj), 2)

    def test_do_get_alarms_by_id(self):
        res = mock.Mock()
        req = mock.Mock()

        req_result = mock.Mock()

        req_result.json.return_value = self.data
        req_result.status_code = 200

        with mock.patch.object(es_conn.ESConnection, 'get_message_by_id',
                               return_value=req_result):
            self.dispatcher_get_by_id.do_get_alarms_by_id(
                req, res, id="d718fb26-d16d-4705-8f02-13a1468619c9")

        # test that the response code is 200
        self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))
        obj = json.loads(res.body)

        # test that the response object has the required properties
        self.assertEqual(obj['id'],
                         "d718fb26-d16d-4705-8f02-13a1468619c9")
        self.assertIsNotNone(obj['metrics'])
        self.assertEqual(obj['state'], 'OK')
        self.assertIsNotNone(obj['sub_alarms'])
        self.assertEqual(obj['created_timestamp'], '2015-06-17T18:43:21Z')
        self.assertEqual(obj['updated_timestamp'], '2015-06-17T18:43:27Z')
        self.assertEqual(obj['state_updated_timestamp'],
                         '2015-06-17T18:43:27Z')

    def test_do_put_alarms(self):
        req = mock.Mock()
        res = mock.Mock()

        req_result = ("{ 'id': 'd718fb26-d16d-4705-"
                      "8f02-13a1468619c9', "
                      "'links': ["
                      "{"
                      "'href': 'http://127.0.0.1:"
                      "9090/v2.0/alarms/'"
                      "'d718fb26-d16d-4705-8f02-"
                      "13a1468619c9', "
                      "'rel': 'self}], '"
                      "'metrics': [{ "
                      "'name': 'cpu.usage', "
                      "'dimensions': { "
                      "'hostname': "
                      "'host7', 'os': 'linux' }}],"
                      "'state': 'OK', "
                      "'sub_alarms': [{"
                      "'sub_alarm_expression': {"
                      "'function': 'AVG', "
                      "'metric_name': "
                      "'cpu.usage', "
                      "'period': '600', "
                      "'threshold': '10', "
                      "'periods': '1', "
                      "'operator': 'LTE', "
                      "'dimensions': {'os': "
                      "'linux'}}, "
                      "'current_values': "
                      "[10.0498869723], "
                      "'sub_alarm_state': 'OK'}], "
                      "'created_timestamp': "
                      "'2015-06-17T16:43:21Z', "
                      "'state_updated_timestamp': "
                      "'2015-06-17T16:43:27Z'"
                      "}")

        json_result = json.dumps(req_result)

        with mock.patch.object(es_conn.ESConnection, 'put_messages',
                               return_value=200):
            with mock.patch.object(req.stream, 'read',
                                   return_value=json_result):
                self.dispatcher_put.do_put_alarms(
                    req, res, id="d718fb26-d16d-4705-8f02-13a1468619c9")
                self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))

    def test_do_delete_alarms(self):
        with mock.patch.object(es_conn.ESConnection, 'del_messages',
                               return_value=200):
            res = mock.Mock()
            self.dispatcher_delete.do_delete_alarms(
                mock.Mock(), res, id="d718fb26-d16d-4705-8f02-13a1468619c9")
            self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))

    def test_do_get_alarms_exception(self):
        res = mock.Mock()
        req = mock.Mock()
        req_result = mock.Mock()

        req_result.json.return_value = ''
        req_result.status_code = 400

        req.query_string = 'metric_dimensions=hostname:h7,os:linux&state=OK'
        with mock.patch.object(es_conn.ESConnection, 'get_messages',
                               return_value=req_result):
            self.dispatcher_get.do_get_alarms(req, res)

        # test that the response code is 400
        self.assertEqual(res.status, getattr(falcon, 'HTTP_400'))

    def test_do_get_alarms_by_id_exception(self):
        res = mock.Mock()
        req = mock.Mock()

        req_result = mock.Mock()

        req_result.json.return_value = ''
        req_result.status_code = 400

        with mock.patch.object(es_conn.ESConnection, 'get_message_by_id',
                               return_value=req_result):
            self.dispatcher_get_by_id.do_get_alarms_by_id(
                req, res, id="d718fb26-d16d-4705-8f02-13a1468619c9")

        # test that the response code is 400
        self.assertEqual(res.status, getattr(falcon, 'HTTP_400'))

    def test_do_put_alarms_exception(self):
        req = mock.Mock()
        res = mock.Mock()

        req_result = ("{ 'id': 'd718fb26-d16d-4705-"
                      "8f02-13a1468619c9', "
                      "'links': ["
                      "{"
                      "'href': 'http://127.0.0.1:"
                      "9090/v2.0/alarms/'"
                      "'d718fb26-d16d-4705-8f02-"
                      "13a1468619c9', "
                      "'rel': 'self}], '"
                      "'metrics': [{ "
                      "'name': 'cpu.usage', "
                      "'dimensions': { "
                      "'hostname': "
                      "'host7', 'os': 'linux' }}],"
                      "'state': 'OK', "
                      "'sub_alarms': [{"
                      "'sub_alarm_expression': {"
                      "'function': 'AVG', "
                      "'metric_name': "
                      "'cpu.usage', "
                      "'period': '600', "
                      "'threshold': '10', "
                      "'periods': '1', "
                      "'operator': 'LTE', "
                      "'dimensions': {'os': "
                      "'linux'}}, "
                      ""
                      "[10.0498869723], "
                      "'sub_alarm_state': 'OK'}], "
                      "'created_timestamp': "
                      "'2015-06-17T16:43:21Z', "
                      "'state_updated_timestamp': "
                      "'2015-06-17T16:43:27Z'"
                      "}")

        json_result = json.dumps(req_result)

        with mock.patch.object(es_conn.ESConnection, 'put_messages',
                               return_value=400,
                               side_effect=Exception('Exception')):
            with mock.patch.object(req.stream, 'read',
                                   return_value=json_result):
                self.dispatcher_put.do_put_alarms(
                    req, res, id="d718fb26-d16d-4705-8f02-13a1468619c9")

                # test that the response code is 400
                self.assertEqual(res.status, getattr(falcon, 'HTTP_400'))

    def test_do_delete_alarms_exception(self):
        with mock.patch.object(es_conn.ESConnection, 'del_messages',
                               return_value=400,
                               side_effect=Exception('Exception')):
            res = mock.Mock()
            self.dispatcher_delete.do_delete_alarms(
                mock.Mock(), res, id="d718fb26-d16d-4705-8f02-13a1468619c9")

            # test that the response code is 400
            self.assertEqual(res.status, getattr(falcon, 'HTTP_400'))
