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

import falcon
import mock
from oslo_config import fixture as fixture_config
from oslotest import base
import requests

from kiloeyes.common import kafka_conn
from kiloeyes.v2.elasticsearch import meters

try:
    import ujson as json
except ImportError:
    import json


class TestMeterDispatcher(base.BaseTestCase):

    def setUp(self):
        super(TestMeterDispatcher, self).setUp()
        self.CONF = self.useFixture(fixture_config.Config()).conf
        self.CONF.set_override('uri', 'fake_url', group='kafka_opts')
        self.CONF.set_override('topic', 'fake', group='meters')
        self.CONF.set_override('doc_type', 'fake', group='meters')
        self.CONF.set_override('index_prefix', 'also_fake', group='meters')
        self.CONF.set_override('index_template', 'etc/metrics.template',
                               group='meters')
        self.CONF.set_override('uri', 'http://fake_es_uri', group='es_conn')

        res = mock.Mock()
        res.status_code = 200
        res.json.return_value = {"data": {"mappings": {"fake": {
            "properties": {
                "dimensions": {"properties": {
                    "key1": {"type": "long"}, "key2": {"type": "long"},
                    "rkey0": {"type": "long"}, "rkey1": {"type": "long"},
                    "rkey2": {"type": "long"}, "rkey3": {"type": "long"}}},
                "name": {"type": "string", "index": "not_analyzed"},
                "timestamp": {"type": "string", "index": "not_analyzed"},
                "value": {"type": "double"}}}}}}
        put_res = mock.Mock()
        put_res.status_code = '200'
        with mock.patch.object(requests, 'get',
                               return_value=res):
            with mock.patch.object(requests, 'put', return_value=put_res):
                self.dispatcher = meters.MeterDispatcher({})

    def test_initialization(self):
        # test that the kafka connection uri should be 'fake' as it was passed
        # in from configuration
        self.assertEqual(self.dispatcher._kafka_conn.uri, 'fake_url')

        # test that the topic is meters as it was passed into dispatcher
        self.assertEqual(self.dispatcher._kafka_conn.topic, 'fake')

        # test that the doc type of the es connection is fake
        self.assertEqual(self.dispatcher._es_conn.doc_type, 'fake')

        self.assertEqual(self.dispatcher._es_conn.uri, 'http://fake_es_uri/')

        # test that the query url is correctly formed
        self.assertEqual(self.dispatcher._query_url, (
            'http://fake_es_uri/also_fake*/fake/_search?search_type=count'))

    def test_post_data(self):
        with mock.patch.object(kafka_conn.KafkaConnection, 'send_messages',
                               return_value=204):
            res = mock.Mock()
            self.dispatcher.post_data(mock.Mock(), res)

        # test that the response code is 204
        self.assertEqual(getattr(falcon, 'HTTP_204'), res.status)

        with mock.patch.object(kafka_conn.KafkaConnection, 'send_messages',
                               return_value=400):
            res = mock.Mock()
            self.dispatcher.post_data(mock.Mock(), res)

        # test that the response code is 204
        self.assertEqual(getattr(falcon, 'HTTP_400'), res.status)

    def test_get_meters(self):
        res = mock.Mock()
        req = mock.Mock()

        def _side_effect(arg):
            if arg == 'name':
                return 'tongli'
            elif arg == 'dimensions':
                return 'key1:100, key2:200'
        req.get_param.side_effect = _side_effect

        req_result = mock.Mock()
        response_str = """
        {"aggregations":{"by_name":{"doc_count_error_upper_bound":0,
        "sum_other_doc_count":0,"buckets":[{"key":"BABMGD","doc_count":300,
        "by_dim":{"buckets":[{"key": "64e6ce08b3b8547b7c32e5cfa5b7d81f",
        "doc_count":300,"meters":{"hits":{"hits":[{ "_type": "metrics",
        "_id": "AVOziWmP6-pxt0dRmr7j", "_index": "data_20160301000000",
        "_source":{"name":"BABMGD",
        "project_id": "35b17138-b364-4e6a-a131-8f3099c5be68",
        "tenant_id": "bd9431c1-8d69-4ad3-803a-8d4a6b89fd36",
        "user_agent": "openstack", "dimensions": null,
        "user": "admin", "value_meta": null, "tenant": "admin",
        "user_id": "efd87807-12d2-4b38-9c70-5f5c2ac427ff"}}]}}}]}}]}}}
        """

        req_result.json.return_value = json.loads(response_str)
        req_result.status_code = 200

        with mock.patch.object(requests, 'post', return_value=req_result):
            self.dispatcher.get_meter(req, res)

        # test that the response code is 200
        self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))
        obj = json.loads(res.body)
        self.assertEqual(obj[0]['name'], 'BABMGD')
        self.assertEqual(obj[0]['meter_id'], 'AVOziWmP6-pxt0dRmr7j')
        self.assertEqual(obj[0]['type'], 'metrics')
        self.assertEqual(obj[0]['user_id'],
                         'efd87807-12d2-4b38-9c70-5f5c2ac427ff')
        self.assertEqual(len(obj), 1)

    def test_post_meters(self):
        with mock.patch.object(kafka_conn.KafkaConnection, 'send_messages',
                               return_value=204):
            res = mock.Mock()
            self.dispatcher.post_meters(mock.Mock(), res)

        self.assertEqual(getattr(falcon, 'HTTP_204'), res.status)
