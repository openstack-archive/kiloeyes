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
import requests

from kiloeyes.common import alarm_expr_parser
from kiloeyes.common import alarm_expr_validator
from kiloeyes.common import es_conn
from kiloeyes.v2.elasticsearch import alarmdefinitions

try:
    import ujson as json
except ImportError:
    import json


class TestAlarmDefinitionUtil(base.BaseTestCase):

    def setUp(self):
        super(TestAlarmDefinitionUtil, self).setUp()
        self.req = mock.Mock()


class TestAlarmDefinitionDispatcher(base.BaseTestCase):

    def setUp(self):
        self.CONF = self.useFixture(fixture_config.Config()).conf
        self.CONF.set_override('doc_type', 'fake', group='alarmdefinitions')
        self.CONF.set_override('uri', 'fake_es_uri', group='es_conn')
        super(TestAlarmDefinitionDispatcher, self).setUp()

        self.dispatcher_get = (
            alarmdefinitions.AlarmDefinitionDispatcher({}))

        self.dispatcher_get_by_id = (
            alarmdefinitions.AlarmDefinitionDispatcher({}))

        self.dispatcher_post = (
            alarmdefinitions.AlarmDefinitionDispatcher({}))

        self.dispatcher_put = (
            alarmdefinitions.AlarmDefinitionDispatcher({}))

        self.dispatcher_delete = (
            alarmdefinitions.AlarmDefinitionDispatcher({}))

        dir_path = os.path.dirname(os.path.realpath(__file__))
        alarms_data_json = open(os.path.join(dir_path,
                                             'test_alarmdefinitions_data')
                                ).read().replace('\n', '')
        self.data = json.loads(alarms_data_json)

    def test_initialization(self):
        # test that the doc type of the es connection is fake
        self.assertEqual(self.dispatcher_get._es_conn.doc_type, 'fake')

        self.assertEqual(self.dispatcher_get._es_conn.uri, 'fake_es_uri/')

    def test_do_get_alarm_definitions(self):
        res = mock.Mock()
        req = mock.Mock()
        req_result = mock.Mock()
        response_str = self.data
        req_result.json.return_value = response_str
        req_result.status_code = 200

        req.query_string = 'name=CPU usage test&dimensions=os:linux'
        with mock.patch.object(es_conn.ESConnection, 'get_messages',
                               return_value=req_result):
            self.dispatcher_get.do_get_alarm_definitions_filtered(req, res)

        # test that the response code is 200
        self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))
        json_result = json.loads(res.body)
        obj = json_result['elements']

        # test that the first response object has the required properties
        self.assertEqual(obj[0]['id'],
                         '8c85be40-bfcb-465c-b450-4eea670806a6')
        self.assertEqual(obj[0]['name'], "CPU usage test")
        self.assertEqual(obj[0]['alarm_actions'],
                         "c60ec47e-5038-4bf1-9f95-4046c6e9a719")
        self.assertEqual(obj[0]['undetermined_actions'],
                         "c60ec47e-5038-4bf1-9t95-4046c6e9a759")
        self.assertEqual(obj[0]['ok_actions'],
                         "c60ec47e-5038-4bf1-9f95-4046cte9a759")
        self.assertEqual(obj[0]['match_by'], "hostname")
        self.assertEqual(obj[0]['severity'], "LOW")
        self.assertEqual(obj[0]['expression'],
                         "max(cpu.usage{os=linux},600)>15")
        self.assertIsNotNone(obj[0]['expression_data'])
        self.assertEqual(obj[0]['description'], "Max CPU 15")

        # test that the second response object has the required properties
        self.assertEqual(obj[1]['id'],
                         'eb43fe12-b442-40b6-aab6-f34450cf90dd')
        self.assertEqual(obj[1]['name'], "CPU usage in last 4 minutes")
        self.assertEqual(obj[1]['alarm_actions'],
                         "c60ec47e-5038-4bf1-9f95-4046c6e9a719")
        self.assertEqual(obj[1]['undetermined_actions'],
                         "c60ec47e-5038-4bf1-9t95-4046c6e9a759")
        self.assertEqual(obj[1]['ok_actions'],
                         "c60ec47e-5038-4bf1-9f95-4046cte9a759")
        self.assertEqual(obj[1]['match_by'], "hostname")
        self.assertEqual(obj[1]['severity'], "LOW")
        self.assertEqual(obj[1]['expression'],
                         "max(cpu.usage,60)>10 times 4")
        self.assertIsNotNone(obj[1]['expression_data'])
        self.assertEqual(obj[1]['description'],
                         "max CPU greater than 10")
        self.assertEqual(len(obj), 2)

    def test_do_get_alarm_definitions_by_id(self):
        res = mock.Mock()
        req = mock.Mock()

        req_result = mock.Mock()

        req_result.json.return_value = self.data
        req_result.status_code = 200

        with mock.patch.object(requests, 'get', return_value=req_result):
            self.dispatcher_get_by_id.do_get_alarm_definitions_by_id(
                req, res, id="72df5ccb-ec6a-4bb4-a15c-939467ccdde0")

        # test that the response code is 200
        self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))
        obj = json.loads(res.body)
        self.assertEqual(obj['id'],
                         "72df5ccb-ec6a-4bb4-a15c-939467ccdde0")
        self.assertEqual(obj['name'], "CPU usage test")
        self.assertEqual(obj['alarm_actions'],
                         "c60ec47e-5038-4bf1-9f95-4046c6e9a719")
        self.assertEqual(obj['undetermined_actions'],
                         "c60ec47e-5038-4bf1-9t95-4046c6e9a759")
        self.assertEqual(obj['ok_actions'],
                         "c60ec47e-5038-4bf1-9f95-4046cte9a759")
        self.assertEqual(obj['match_by'], "hostname")
        self.assertEqual(obj['severity'], "LOW")
        self.assertEqual(obj['expression'],
                         "max(cpu.usage{os=linux},600)>15")
        self.assertEqual(obj['description'], "Max CPU 15")

    def test_do_post_alarm_definitions(self):
        req = mock.Mock()
        res = mock.Mock()
        req_result = mock.Mock()
        req_result.status_code = 201

        with mock.patch.object(requests, 'post', return_value=req_result):
            with mock.patch.object(req.stream, 'read',
                                   return_value="{ 'name': 'CPU usage test', "
                                                "'alarm_actions': "
                                                "'c60ec47e-5038-4bf1-9f95-"
                                                "4046c6e9a719', "
                                                "'undetermined_actions': "
                                                "'c60ec47e-5038-4bf1-9t95-"
                                                "4046c6e9a759', 'ok_actions':"
                                                " 'c60ec47e-5038-4bf1-9f95-"
                                                "4046cte9a759', "
                                                "'match_by': 'hostname', "
                                                "'severity': 'LOW', "
                                                "'expression': "
                                                "'max(cpu.usage{os=linux},"
                                                "600)"
                                                ">15', 'description': "
                                                "'Max CPU 15'"
                                                "}"
                                   ):
                self.dispatcher_post.do_post_alarm_definitions(
                    req, res)
                self.assertEqual(res.status, getattr(falcon, 'HTTP_201'))

    def test_do_put_alarm_definitions(self):
        req = mock.Mock()
        res = mock.Mock()
        req_result = mock.Mock()
        req_result.status_code = 200
        req_get_result = mock.Mock()

        req_get_result.json.return_value = self.data
        req_get_result.status_code = 200

        with mock.patch.object(requests, 'get', return_value=req_get_result):
            with mock.patch.object(requests, 'put', return_value=req_result):
                with mock.patch.object(
                        req.stream, 'read',
                        return_value="{ 'name': 'CPU usage test', "
                                     "'alarm_actions': "
                                     "'c60ec47e-5038-4bf1-9f95-"
                                     "4046c6e9a719', "
                                     "'undetermined_actions': "
                                     "'c60ec47e-5038-4bf1-9t95-"
                                     "4046c6e9a759', 'ok_actions':"
                                     " 'c60ec47e-5038-4bf1-9f95-"
                                     "4046cte9a759', "
                                     "'match_by': 'hostname', "
                                     "'severity': 'LOW', "
                                     "'expression': "
                                     "'max(cpu.usage{os=linux},"
                                     "600)"
                                     ">15', 'description': "
                                     "'Max CPU 15'"
                                     "}"
                ):
                    self.dispatcher_put.do_put_alarm_definitions(
                        req, res, id="8c85be40-bfcb-465c-b450-4eea670806a6")
                    self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))

    def test_do_delete_alarm_definitions(self):
        with mock.patch.object(es_conn.ESConnection, 'del_messages',
                               return_value=200):
            res = mock.Mock()
            self.dispatcher_delete.do_delete_alarm_definitions(
                mock.Mock(), res, id="72df5ccb-ec6a-4bb4-a15c-939467ccdde0")
            self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))

    def test_do_delete_alarm_definitions_exception(self):
        with mock.patch.object(es_conn.ESConnection, 'del_messages',
                               return_value=0,
                               side_effect=Exception('Exception')):
            res = mock.Mock()
            self.dispatcher_delete.do_delete_alarm_definitions(
                mock.Mock(), res, id="72df5ccb-ec6a-4bb4-a15c-939467ccdde0")
            self.assertEqual(res.status, getattr(falcon, 'HTTP_400'))

    def test_do_get_alarm_definitions_filtered_exception(self):
        res = mock.Mock()
        req = mock.Mock()
        req_result = mock.Mock()

        req_result.json.return_value = ''
        req_result.status_code = 400
        req.query_string = 'name=CPU usage test&dimensions=os:linux'
        with mock.patch.object(es_conn.ESConnection, 'get_messages',
                               return_value=req_result):
            self.dispatcher_get.do_get_alarm_definitions_filtered(req, res)

            # test that the response code is 400
            self.assertEqual(res.status, getattr(falcon, 'HTTP_400'))

    def test_do_post_alarm_definitions_exception(self):
        req = mock.Mock()
        res = mock.Mock()
        req_result = mock.Mock()
        req_result.status_code = 201

        with mock.patch.object(requests, 'post', return_value=req_result):
            with mock.patch.object(req.stream, 'read',
                                   return_value="{ 'name': 'CPU usage test', "
                                                "'alarm_actions': "
                                                "'c60ec47e-5038-4bf1-9f95-"
                                                "4046c6e9a719', "
                                                "'undetermined_actions': "
                                                "'c60ec47e-5038-4bf1-9t95-"
                                                "4046c6e9a759', 'ok_actions':"
                                                " 'c60ec47e-5038-4bf1-9f95-"
                                                "4046cte9a759', "
                                                "'match_by': 'hostname', "
                                                "'severity': 'LOW', "
                                                "'expression': "
                                                "'max(cpu.usage{os=linux},"
                                                "600)"
                                                ">15', 'description': "
                                                "'Max CPU 15'"
                                                "}"
                                   ):
                with mock.patch.object(alarm_expr_validator,
                                       'is_valid_alarm_definition',
                                       return_value=False):
                    self.dispatcher_post.do_post_alarm_definitions(
                        req, res)
                    # test that the response code is 400
                    self.assertEqual(res.status, getattr(falcon, 'HTTP_400'))

    def test_do_post_alarm_definitions_parse_exception(self):
        req = mock.Mock()
        res = mock.Mock()
        req_result = mock.Mock()
        req_result.status_code = 201

        with mock.patch.object(requests, 'post', return_value=req_result):
            with mock.patch.object(req.stream, 'read',
                                   return_value="{ 'name': 'CPU usage test', "
                                                "'alarm_actions': "
                                                "'c60ec47e-5038-4bf1-9f95-"
                                                "4046c6e9a719', "
                                                "'undetermined_actions': "
                                                "'c60ec47e-5038-4bf1-9t95-"
                                                "4046c6e9a759', 'ok_actions':"
                                                " 'c60ec47e-5038-4bf1-9f95-"
                                                "4046cte9a759', "
                                                "'match_by': 'hostname', "
                                                "'severity': 'TEST', "
                                                "'expression': "
                                                "'max(cpu.usage{os=linux},"
                                                "600)"
                                                ">15', 'description': "
                                                "'Max CPU 15'"
                                                "}"
                                   ):
                with mock.patch.object(alarm_expr_validator,
                                       'is_valid_alarm_definition',
                                       return_value=True):
                    with mock.patch.object(alarm_expr_parser,
                                           'AlarmExprParser',
                                           return_value=None,
                                           side_effect=(Exception('Exc'
                                                                  'eption'))):
                        self.dispatcher_post.do_post_alarm_definitions(
                            req, res)
                        # test that the response code is 400
                        self.assertEqual(res.status, getattr(falcon,
                                                             'HTTP_400'))

    def test_do_put_alarm_definitions_exception(self):
        req = mock.Mock()
        res = mock.Mock()
        req_result = mock.Mock()
        req_result.status_code = 400
        req_get_result = mock.Mock()

        req_get_result.json.return_value = self.data
        req_get_result.status_code = 200

        with mock.patch.object(requests, 'get', return_value=req_get_result):
            with mock.patch.object(requests, 'put', return_value=req_result):
                with mock.patch.object(
                        req.stream, 'read',
                        return_value="{ 'name': 'CPU usage test', "
                                     ""
                                     "'c60ec47e-5038-4bf1-9f95-"
                                     "4046c6e9a719', "
                                     "'undetermined_actions': "
                                     "'c60ec47e-5038-4bf1-9t95-"
                                     "4046c6e9a759', 'ok_actions':"
                                     " 'c60ec47e-5038-4bf1-9f95-"
                                     "4046cte9a759', "
                                     "'match_by': 'hostname', "
                                     "'severity': 'LOW', "
                                     "'expression': "
                                     "'max(cpu.usage{os=linux},"
                                     "600)"
                                     ">15', 'description': "
                                     "'Max CPU 15'"
                                     "}"
                ):
                    with mock.patch.object(alarm_expr_validator,
                                           'is_valid_alarm_definition',
                                           return_value=False):
                        with mock.patch.object(
                                alarm_expr_parser.AlarmExprParser,
                                'sub_alarm_expressions', return_value=None,
                                side_effect=(Exception('Exception'))):
                            self.dispatcher_put.do_put_alarm_definitions(
                                req, res,
                                id="8c85be40-bfcb-465c-b450-4eea670806a6")
                            # test that the response code is 400
                            self.assertEqual(res.status, getattr(falcon,
                                                                 'HTTP_400'))

    def test_do_put_alarm_definitions_else_exception(self):
        req = mock.Mock()
        res = mock.Mock()
        req_result = mock.Mock()
        req_result.status_code = 400
        req_get_result = mock.Mock()

        req_get_result.json.return_value = self.data
        req_get_result.status_code = 200

        with mock.patch.object(requests, 'get', return_value=req_get_result):
            with mock.patch.object(requests, 'put', return_value=req_result):
                with mock.patch.object(
                        req.stream, 'read',
                        return_value="{ 'name': 'CPU usage test', "
                                     "'alarm_actions': "
                                     "'c60ec47e-5038-4bf1-9f95-"
                                     "4046c6e9a719', "
                                     "'undetermined_actions': "
                                     "'c60ec47e-5038-4bf1-9t95-"
                                     "4046c6e9a759', 'ok_actions':"
                                     " 'c60ec47e-5038-4bf1-9f95-"
                                     "4046cte9a759', "
                                     "'match_by': 'hostname', "
                                     "'severity': 'LOW', "
                                     "'expression': "
                                     "'max(cpu.usage{os=linux},"
                                     "600)"
                                     ">15', 'description': "
                                     "'Max CPU 15'"
                                     "}"
                ):
                    with mock.patch.object(alarm_expr_validator,
                                           'is_valid_alarm_definition',
                                           return_value=False):
                        with mock.patch.object(
                                alarm_expr_parser.AlarmExprParser,
                                'sub_alarm_expressions', return_value=None,
                                side_effect=(Exception('Exception'))):
                            self.dispatcher_put.do_put_alarm_definitions(
                                req, res,
                                id="8c85be40-bfcb-465c-b450-4eea670806a6")
                            # test that the response code is 400
                            self.assertEqual(res.status, getattr(falcon,
                                                                 'HTTP_400'))

    def test_do_get_alarm_definitions_by_id_exception(self):
        res = mock.Mock()
        req = mock.Mock()
        req_result = mock.Mock()

        req_result.json.return_value = ''
        req_result.status_code = 400

        with mock.patch.object(es_conn.ESConnection, 'get_message_by_id',
                               return_value=req_result):
            self.dispatcher_get_by_id.do_get_alarm_definitions_by_id(
                req, res, id="72df5ccb-ec6a-4bb4-a15c-939467ccdde0")

            # test that the response code is 400
            self.assertEqual(res.status, getattr(falcon, 'HTTP_400'))
