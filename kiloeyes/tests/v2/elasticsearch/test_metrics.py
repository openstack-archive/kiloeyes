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
from kiloeyes.v2.elasticsearch import metrics

try:
    import ujson as json
except ImportError:
    import json


class TestParamUtil(base.BaseTestCase):

    def setUp(self):
        super(TestParamUtil, self).setUp()
        self.req = mock.Mock()
        self.req.get_param.side_effect = self._side_effect

    def _side_effect(self, arg):
        if arg == 'name':
            return 'tongli'
        elif arg == 'dimensions':
            return 'key1:100, key2:200'
        elif arg == 'start_time':
            return '2015-01-31T13:35:00Z'
        elif arg == 'end_time':
            return '2015-11-30T14:05:00Z'
        elif arg == 'period':
            return '200'
        elif arg == 'statistics':
            return 'sum, avg'

    def test_common(self):
        result = [{'match': {'name': 'tongli'}},
                  {'range': {'timestamp': {'gte': 1422711300.0,
                                           'lt': 1448892300.0}}},
                  {'match': {'dimensions.key1': 100.0}},
                  {'match': {'dimensions.key2': 200.0}}]

        q = []
        ret = metrics.ParamUtil.common(self.req, q)
        self.assertEqual(q, result)
        self.assertTrue(ret)

    def test_period(self):
        ret = metrics.ParamUtil.period(self.req)
        self.assertEqual(ret, '200s')

    def test_stats(self):
        ret = metrics.ParamUtil.stats(self.req)
        self.assertEqual(ret, ['sum', 'avg'])


class TestMetricDispatcher(base.BaseTestCase):

    def setUp(self):
        super(TestMetricDispatcher, self).setUp()
        self.CONF = self.useFixture(fixture_config.Config()).conf
        self.CONF.set_override('uri', 'fake_url', group='kafka_opts')
        self.CONF.set_override('topic', 'fake', group='metrics')
        self.CONF.set_override('doc_type', 'fake', group='metrics')
        self.CONF.set_override('index_prefix', 'also_fake', group='metrics')
        self.CONF.set_override('index_template', 'etc/metrics.template',
                               group='metrics')
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
                self.dispatcher = metrics.MetricDispatcher({})

    def test_initialization(self):
        # test that the kafka connection uri should be 'fake' as it was passed
        # in from configuration
        self.assertEqual(self.dispatcher._kafka_conn.uri, 'fake_url')

        # test that the topic is metrics as it was passed into dispatcher
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

    def test_do_get_metrics(self):
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
        "doc_count":300,"metrics":{"hits":{"hits":[{
        "_source":{"name":"BABMGD","dimensions":{"key2":"NVITDU",
        "key1":"FUFMPY","key_43":"ROQBZM"}}}]}}}]}},
        {"key":"BABSYZ","doc_count":300,"by_dim":{"buckets":[{
        "key":"84863c7cfee6837a77eb476ea9f35f87","doc_count":300,
        "metrics":{"hits":{"hits":[{"_source":{"name":"BABSYZ",
        "dimensions":{"key2":"UIPAJD","key1":"DKPNKA",
        "key_10": "RADAJP"}}}]}}}]}}]}}}
        """

        req_result.json.return_value = json.loads(response_str)
        req_result.status_code = 200

        with mock.patch.object(requests, 'post', return_value=req_result):
            self.dispatcher.do_get_metrics(req, res)

        # test that the response code is 200
        self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))
        obj = json.loads(res.body)
        self.assertEqual(obj[0]['name'], 'BABMGD')
        self.assertEqual(obj[0]['dimensions']['key2'], 'NVITDU')
        self.assertEqual(len(obj), 2)

    def test_do_post_metrics(self):
        with mock.patch.object(kafka_conn.KafkaConnection, 'send_messages',
                               return_value=204):
            res = mock.Mock()
            self.dispatcher.do_post_metrics(mock.Mock(), res)

        self.assertEqual(getattr(falcon, 'HTTP_204'), res.status)

    def test_do_get_measurements(self):
        res = mock.Mock()
        req = mock.Mock()

        def _side_effect(arg):
            if arg == 'name':
                return 'tongli'
            elif arg == 'dimensions':
                return 'key1:100, key2:200'
            elif arg == 'start_time':
                return '2014-01-01'

        req.get_param.side_effect = _side_effect

        req_result = mock.Mock()
        response_str = """
        {"took":226,"timed_out":false,"_shards":{"total":5,"successful":5,
        "failed":0},"hits":{"total":6600,"max_score":0.0,"hits":[]},
        "aggregations":{"by_name":{"doc_count_error_upper_bound":293,
        "sum_other_doc_count":5791,"buckets":[{"key":"ABYTPK",
        "doc_count":300,"by_dim":{"doc_count_error_upper_bound":0,
        "sum_other_doc_count":0,
        "buckets":[{"key":"e62ef04ee44abcccdd177087d159c1e3","doc_count":300,
        "dimension":{"hits":{"total":300,"max_score":1.4142135,
        "hits":[{"_index":"data_20150121","_type":"metrics",
        "_id":"AUsShaLKTZaMxA7_0_Hj","_score":1.4142135,
        "_source":{"name":"ABYTPK","dimensions":{"key_81":"MKKNSA",
        "key2":"TJJQGE","key1":"GYYLEG"}}}]}},
        "measures":{"hits":{"total":300,"max_score":null,
        "hits":[{"_index":"data_20150121","_type":"metrics",
        "_id":"AUsShaKuTZaMxA7_0_Hd","_score":null,
        "_source":{"timestamp":1.421944922765286E9,"value":0.0},
        "sort":[1.421944922765286E9]},{"_index":"data_20150121",
        "_type":"metrics","_id":"AUsShaM8TZaMxA7_0_H7",
        "_score":null,"_source":{"timestamp":1.421944922907783E9,
        "value":0.0},"sort":[1.421944922907783E9]},{"_index":"data_20150121",
        "_type":"metrics","_id":"AUsShaR2TZaMxA7_0_IZ","_score":null,
        "_source":{"timestamp":1.421944923222439E9,"value":0.0},
        "sort":[1.421944923222439E9]}]}}}]}},{"key":"ABUYPI","doc_count":256,
        "by_dim":{"doc_count_error_upper_bound":0,"sum_other_doc_count":0,
        "buckets":[{"key":"3dba425d350f6f46f8eda8a883231e58",
        "doc_count":256,"dimension":{"hits":{"total":256,
        "max_score":1.4142135,"hits":[{"_index":"data_20150121",
        "_type":"metrics","_id":"AUsSaTfYTZaMxA7_zaxn","_score":1.4142135,
        "_source":{"name":"ABUYPI","dimensions":{"key2":"BEBGIY",
        "key1":"JZAZQS","key_67":"EAJWVV"}}}]}},
        "measures":{"hits":{"total":256,"max_score":null,
        "hits":[{"_index":"data_20150121","_type":"metrics",
        "_id":"AUsSaTfQTZaMxA7_zaxl","_score":null,
        "_source":{"timestamp":1.421943060399819E9,"value":0.0},
        "sort":[1.421943060399819E9]},{"_index":"data_20150121",
        "_type":"metrics","_id":"AUsSaThJTZaMxA7_zayD","_score":null,
        "_source":{"timestamp":1.421943060519964E9,"value":0.0},
        "sort":[1.421943060519964E9]},{"_index":"data_20150121",
        "_type":"metrics","_id":"AUsSaTjKTZaMxA7_zayh","_score":null,
        "_source":{"timestamp":1.421943060648909E9,"value":0.0},
        "sort":[1.421943060648909E9]}]}}}]}},
        {"key":"ABEPJR","doc_count":253,
        "by_dim":{"doc_count_error_upper_bound":0,"sum_other_doc_count":0,
        "buckets":[{"key":"6d6bbdda3ed7f14c76e746e2fbd52a37",
        "doc_count":253,"dimension":{"hits":{"total":253,
        "max_score":1.4142135,"hits":[{"_index":"data_20150121",
        "_type":"metrics","_id":"AUsR6STQTZaMxA7_sjp6",
        "_score":1.4142135,"_source":{"name":"ABEPJR",
        "dimensions":{"key_7":"ZAUVQN","key2":"NSXBUW","key1":"UXTDSW"}}}]}},
        "measures":{"hits":{"total":253,"max_score":null,
        "hits":[{"_index":"data_20150121","_type":"metrics",
        "_id":"AUsR6SItTZaMxA7_sjnV","_score":null,
        "_source":{"timestamp":1.421934666252589E9,"value":0.0},
        "sort":[1.421934666252589E9]},{"_index":"data_20150121",
        "_type":"metrics","_id":"AUsR6SKqTZaMxA7_sjnz","_score":null,
        "_source":{"timestamp":1.421934666377047E9,"value":0.0},
        "sort":[1.421934666377047E9]},{"_index":"data_20150121",
        "_type":"metrics","_id":"AUsR6SMiTZaMxA7_sjoR","_score":null,
        "_source":{"timestamp":1.421934666497888E9,"value":0.0},
        "sort":[1.421934666497888E9]}]}}}]}}]}}}
        """
        req_result.json.return_value = json.loads(response_str)

        req_result.status_code = 200

        with mock.patch.object(requests, 'post', return_value=req_result):
            self.dispatcher.do_get_measurements(req, res)

        # test that the response code is 200
        self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))
        obj = json.loads(res.body)

        # there should be total of 3 objects
        self.assertEqual(len(obj), 3)
        self.assertIsNotNone(obj[0]['name'])
        self.assertIsNotNone(obj[0]['dimensions'])
        self.assertIsNotNone(obj[0]['columns'])
        self.assertIsNotNone(obj[0]['measurements'])

    def test_do_get_statistics(self):
        res = mock.Mock()
        req = mock.Mock()

        def _side_effect(arg):
            if arg == 'name':
                return 'tongli'
            elif arg == 'dimensions':
                return 'key1:100, key2:200'
            elif arg == 'start_time':
                return '2014-01-01'
            elif arg == 'end_time':
                return None
            elif arg == 'period':
                return None
            elif arg == 'statistics':
                return 'avg, sum, max'

        req.get_param.side_effect = _side_effect

        req_result = mock.Mock()
        response_str = """
        {"took":2006,"timed_out":false,"_shards":{"total":5,"successful":5,
        "failed":0},"hits":{"total":600,"max_score":0.0,"hits":[]},
        "aggregations":{"by_name":{"doc_count_error_upper_bound":0,
        "sum_other_doc_count":0,"buckets":[{"key":"BABMGD","doc_count":300,
        "by_dim":{"doc_count_error_upper_bound":0,"sum_other_doc_count":0,
        "buckets":[{"key":"64e6ce08b3b8547b7c32e5cfa5b7d81f","doc_count":300,
        "periods":{"buckets":[{"key":1421700000,"doc_count":130,
        "statistics":{"count":130,"min":0.0,"max":595.0274095324651,
        "avg":91.83085293930924,"sum":11938.0108821102}},
        {"key":1422000000,"doc_count":170,"statistics":{"count":170,
        "min":0.0,"max":1623.511307756313,"avg":324.69434786459897,
        "sum":55198.039136981824}}]},"dimension":{"hits":{"total":300,
        "max_score":1.4142135,"hits":[{"_index":"data_20150121",
        "_type":"metrics","_id":"AUsSNF5mTZaMxA7_wmFx","_score":1.4142135,
        "_source":{"name":"BABMGD","dimensions":{"key2":"NVITDU",
        "key1":"FUFMPY","key_43":"ROQBZM"}}}]}}}]}},{"key":"BABSYZ",
        "doc_count":300,"by_dim":{"doc_count_error_upper_bound":0,
        "sum_other_doc_count":0,
        "buckets":[{"key":"84863c7cfee6837a77eb476ea9f35f87","doc_count":300,
        "periods":{"buckets":[{"key":1421700000,"doc_count":130,
        "statistics":{"count":130,"min":0.0,"max":588.7273873368565,
        "avg":100.45023098906705,"sum":13058.530028578716}},
        {"key":1422000000,"doc_count":170,"statistics":{"count":170,
        "min":0.0,"max":1515.5538517109185,"avg":332.5777043693029,
        "sum":56538.209742781495}}]},"dimension":{"hits":{"total":300,
        "max_score":1.4142135,"hits":[{"_index":"data_20150121",
        "_type":"metrics","_id":"AUsR7oGETZaMxA7_s0Y0","_score":1.4142135,
        "_source":{"name":"BABSYZ","dimensions":{"key2":"UIPAJD",
        "key1":"DKPNKA","key_10":"RADAJP"}}}]}}}]}}]}}}
        """
        req_result.json.return_value = json.loads(response_str)

        req_result.status_code = 200

        with mock.patch.object(requests, 'post', return_value=req_result):
            self.dispatcher.do_get_statistics(req, res)

        # test that the response code is 200
        self.assertEqual(res.status, getattr(falcon, 'HTTP_200'))
        obj = json.loads(res.body)
        # there should be total of 2 objects
        self.assertEqual(len(obj), 2)
        self.assertIsNotNone(obj[0]['name'])
        self.assertIsNotNone(obj[0]['dimensions'])
        self.assertIsNotNone(obj[0]['columns'])
        self.assertEqual(obj[0]['columns'],
                         ["timestamp", "avg", "sum", "max"])
        self.assertIsNotNone(obj[0]['statistics'])
