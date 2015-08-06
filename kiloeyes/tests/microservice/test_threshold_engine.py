# Copyright 2015 Carnegie Mellon University
##
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import mock
from oslo_config import fixture as fixture_config
from oslotest import base
from stevedore import driver

from kiloeyes.common import es_conn
from kiloeyes.common import kafka_conn
from kiloeyes.microservice import threshold_engine as engine


class TestThresholdEngine(base.BaseTestCase):
    def setUp(self):
        self.CONF = self.useFixture(fixture_config.Config()).conf
        self.CONF.kafka_opts.uri = 'fake_url'
        self.CONF.thresholdengine.metrics_topic = 'fake_metrics'
        self.CONF.thresholdengine.alarm_topic = 'fake_alarms'
        self.CONF.thresholdengine.check_alarm_interval = 10

        self.CONF.alarmdefinitions.index_strategy = ''
        self.CONF.alarmdefinitions.doc_type = 'fake_doc_type'
        self.CONF.alarmdefinitions.dimensions = 'fake_key:fake_value'
        self.CONF.alarmdefinitions.name = 'fake_name'
        self.CONF.alarmdefinitions.check_alarm_def_interval = 120

        self.CONF.es_conn.uri = 'fake_es_url'
        super(TestThresholdEngine, self).setUp()
        self.thresh_engine = engine.ThresholdEngine()

    def test_initialization(self):
        params = {'query': {
            'bool': {'must': [
                {'query_string': {
                    'default_field': 'alarmdefinitions.expression_data.'
                                     'dimensions.fake_key',
                    'query': 'fake_value'}},
                {'query_string': {'default_field': 'name',
                                  'query': 'fake_name'}}]}}}
        # Test Kafka connection uri and topic
        self.assertEqual(self.thresh_engine.thread_metrics.
                         _consume_kafka_conn.uri, 'fake_url')
        self.assertEqual(self.thresh_engine.thread_metrics.
                         _consume_kafka_conn.topic, 'fake_metrics')

        self.assertEqual(self.thresh_engine.thread_alarm_def.params, params)
        self.assertEqual(self.thresh_engine.thread_alarm_def.interval, 120)
        self.assertEqual(self.thresh_engine.
                         thread_alarm_def._es_conn.doc_type, 'fake_doc_type')
        self.assertEqual(self.thresh_engine.
                         thread_alarm_def._es_conn.uri, 'fake_es_url/')

        self.assertEqual(self.thresh_engine.thread_alarm.
                         _publish_kafka_conn.uri, 'fake_url')
        self.assertEqual(self.thresh_engine.thread_alarm.
                         _publish_kafka_conn.topic, 'fake_alarms')
        self.assertEqual(self.thresh_engine.thread_alarm.interval, 10)

    def get_response_str(self, fake_alarm_def):
        ad_list = []
        for ad in fake_alarm_def:
            ad_list.append({'_source': ad})
        return {"hits": {"hits": ad_list}}

    def test_refresh_alarm_definitions(self):
        # test refresh alarm definitions
        ad = [{'id': 'fake_id_0', 'expression': 'fake_expr_0'},
              {'id': 'fake_id_1', 'expression': 'fake_expr_1'},
              {'id': 'fake_id_2', 'expression': 'fake_expr_2'}]
        res = mock.Mock()
        res.status_code = 200
        response_json = self.get_response_str(ad)
        res.json.return_value = response_json
        processor = mock.Mock()
        with mock.patch.object(driver.DriverManager, '__init__',
                               return_value=None):
            with mock.patch.object(driver.DriverManager, 'driver',
                                   return_value=processor):
                with mock.patch.object(es_conn.ESConnection, 'get_messages',
                                       return_value=res):
                    (self.thresh_engine.thread_alarm_def.
                     refresh_alarm_processors())
        print (self.thresh_engine.thread_alarm_def.threshold_processors)
        tp = self.thresh_engine.thread_alarm_def.threshold_processors
        self.assertEqual(3, len(tp))
        self.assertIn('fake_id_1', tp)
        self.assertIn('fake_id_2', tp)
        self.assertNotIn('fake_id_3', tp)

        ad = [{'id': 'fake_id_3', 'expression': 'fake_expr_3'},
              {'id': 'fake_id_1', 'expression': 'fake_expr_update'},
              {'id': 'fake_id_2', 'expression': 'fake_expr_2'}]
        res = mock.Mock()
        res.status_code = 200
        response_json = self.get_response_str(ad)
        res.json.return_value = response_json
        processor = mock.Mock()
        with mock.patch.object(driver.DriverManager, '__init__',
                               return_value=None):
            with mock.patch.object(driver.DriverManager, 'driver',
                                   return_value=processor):
                with mock.patch.object(es_conn.ESConnection, 'get_messages',
                                       return_value=res):
                    (self.thresh_engine.thread_alarm_def.
                     refresh_alarm_processors())
        print (self.thresh_engine.thread_alarm_def.threshold_processors)
        tp = self.thresh_engine.thread_alarm_def.threshold_processors
        self.assertEqual(3, len(tp))
        self.assertNotIn('fake_id_0', tp)
        self.assertIn('fake_id_2', tp)
        self.assertIn('fake_id_3', tp)
        self.assertEqual('fake_expr_update',
                         tp['fake_id_1']['json']['expression'])

        # test http request fails
        ad = []
        res = mock.Mock()
        res.status_code = 201
        response_json = self.get_response_str(ad)
        res.json.return_value = response_json
        processor = mock.Mock()
        with mock.patch.object(driver.DriverManager, '__init__',
                               return_value=None):
            with mock.patch.object(driver.DriverManager, 'driver',
                                   return_value=processor):
                with mock.patch.object(es_conn.ESConnection, 'get_messages',
                                       return_value=res):
                    (self.thresh_engine.thread_alarm_def.
                     refresh_alarm_processors())
        print (self.thresh_engine.thread_alarm_def.threshold_processors)
        tp = self.thresh_engine.thread_alarm_def.threshold_processors
        self.assertEqual(3, len(tp))

    def test_consume_metrics(self):
        # test consume received metrics
        raw_metrics = [
            '{"timestamp": "2015-06-25T14:01:36Z", "name": "biz1", '
            '"value": 1300, '
            '"dimensions": {"key2": "value2", "hostname": "h1"}}',
            '{"timestamp": "2015-06-25T14:01:36Z", "name": "biz2", '
            '"value": 1500, '
            '"dimensions": {"key2": "value2", "hostname": "h2"}}',
            '{"timestamp": "2015-06-25T14:01:36Z", "name": "biz3", '
            '"value": 1200, '
            '"dimensions": {"key2": "value2", "hostname": "h3"}}']
        metrics = [mock.Mock(), mock.Mock(), mock.Mock()]
        for i in range(len(raw_metrics)):
            metrics[i].message.value = raw_metrics[i]
        pre = self.thresh_engine.thread_metrics.threshold_processors.copy()
        with mock.patch.object(kafka_conn.KafkaConnection, 'get_messages',
                               return_value=metrics):
            self.thresh_engine.thread_metrics.read_metrics()
        self.assertEqual(pre,
                         self.thresh_engine.thread_metrics.
                         threshold_processors)

        # read one alarm definition and test consume metrics again
        processor = mock.Mock()
        res = mock.Mock()
        res.status_code = 200
        response_json = self.get_response_str([{'id': 'fake_id_1'}])
        res.json.return_value = response_json
        with mock.patch.object(driver.DriverManager, '__init__',
                               return_value=None):
            with mock.patch.object(driver.DriverManager, 'driver',
                                   return_value=processor):
                with mock.patch.object(es_conn.ESConnection, 'get_messages',
                                       return_value=res):
                    (self.thresh_engine.thread_alarm_def.
                     refresh_alarm_processors())
        pre = self.thresh_engine.thread_metrics.threshold_processors.copy()
        with mock.patch.object(kafka_conn.KafkaConnection, 'get_messages',
                               return_value=metrics):
            self.thresh_engine.thread_metrics.read_metrics()
        self.assertEqual(pre,
                         self.thresh_engine.thread_metrics.
                         threshold_processors)
        print (self.thresh_engine.thread_metrics.threshold_processors)

    def test_publish_alarms(self):
        # read one alarm definition
        processor = mock.Mock()
        res = mock.Mock()
        res.status_code = 200
        response_json = self.get_response_str([{'id': 'fake_id_1'}])
        res.json.return_value = response_json
        with mock.patch.object(driver.DriverManager, '__init__',
                               return_value=None):
            with mock.patch.object(driver.DriverManager, 'driver',
                                   return_value=processor):
                with mock.patch.object(es_conn.ESConnection, 'get_messages',
                                       return_value=res):
                    (self.thresh_engine.thread_alarm_def.
                     refresh_alarm_processors())

        # test send alarms
        pre = self.thresh_engine.thread_alarm.threshold_processors.copy()
        with mock.patch.object(kafka_conn.KafkaConnection, 'send_messages',
                               return_value=None):
            self.thresh_engine.thread_alarm.send_alarm()
        self.assertEqual(pre,
                         self.thresh_engine.thread_alarm.
                         threshold_processors)
