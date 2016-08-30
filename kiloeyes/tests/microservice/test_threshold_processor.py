#
# Copyright 2015 Carnegie Mellon University
#
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

import json
import mock
import os
from oslo_log import log

from kiloeyes.common import timeutils as tu
from kiloeyes.microservice import threshold_processor as processor
from kiloeyes import tests

LOG = log.getLogger(__name__)


class TestCaseUtil(object):
    def __init__(self):
        path = os.path.split(os.path.realpath(__file__))[0]
        path += '/test_case_threshold_processor.json'
        f = open(path)
        try:
            self.test_cases = json.load(f)
        finally:
            f.close()

    def get_alarm_def(self, name):
        return self.test_cases["alarm_def"][name]

    def get_metrics(self, name):
        ts = self.test_cases["metrics"][name]
        for t in ts:
            o = t["time_offset"]
            t["timestamp"] = tu.utcnow_ts() + o
            yield json.dumps(t)


class TestThresholdProcessor(tests.BaseTestCase):
    def setUp(self):
        super(TestThresholdProcessor, self).setUp()
        self.util = TestCaseUtil()

    def test__init_(self):
        """Test processor _init_.

        If alarm definition is not in standard format,
        the processor cannot be successfully initialized.
        Alarm_definition3 is a bad one.
        Processor _init_ will fail on this case.
        """
        tp = None
        try:
            ad = self.util.get_alarm_def("alarm_def_utf8")
            tp = processor.ThresholdProcessor(ad)
        except Exception:
            tp = None
        self.assertIsInstance(tp, processor.ThresholdProcessor)
        try:
            ad = self.util.get_alarm_def("alarm_def_match_by")
            tp = processor.ThresholdProcessor(ad)
        except Exception:
            tp = None
        self.assertIsInstance(tp, processor.ThresholdProcessor)
        try:
            ad = self.util.get_alarm_def("alarm_def_periods")
            tp = processor.ThresholdProcessor(ad)
        except Exception:
            tp = None
        self.assertIsInstance(tp, processor.ThresholdProcessor)
        try:
            ad = self.util.get_alarm_def("alarm_def_wrong")
            tp = processor.ThresholdProcessor(ad)
        except Exception:
            tp = None
        self.assertIsNone(tp)

    def test_process_alarms(self):
        """Test if alarm is correctly produced."""

        # test utf8 dimensions and compound logic expr
        # init processor
        ad = self.util.get_alarm_def("alarm_def_utf8")
        tp = processor.ThresholdProcessor(ad)
        # send metrics to the processor
        metrics_list = self.util.get_metrics("metrics_utf8")
        for metrics in metrics_list:
            timestamp = json.loads(metrics)['timestamp']
            with mock.patch.object(tu, 'utcnow_ts',
                                   return_value=timestamp):
                tp.process_metrics(metrics)
        # manually call the function to update alarms
        alarms = tp.process_alarms()
        self.assertEqual(1, len(alarms))
        self.assertEqual('ALARM', json.loads(alarms[0])['state'])

        # test more than 1 periods
        ad = self.util.get_alarm_def("alarm_def_periods")
        tp = processor.ThresholdProcessor(ad)
        metrics_list = self.util.get_metrics("metrics_periods_0")
        for metrics in metrics_list:
            timestamp = json.loads(metrics)['timestamp']
            with mock.patch.object(tu, 'utcnow_ts',
                                   return_value=timestamp):
                tp.process_metrics(metrics)
        alarms = tp.process_alarms()
        self.assertEqual(1, len(alarms))
        self.assertEqual('OK', json.loads(alarms[0])['state'])
        ad = self.util.get_alarm_def("alarm_def_periods")
        tp = processor.ThresholdProcessor(ad)
        metrics_list = self.util.get_metrics("metrics_periods_1")
        for metrics in metrics_list:
            timestamp = json.loads(metrics)['timestamp']
            with mock.patch.object(tu, 'utcnow_ts',
                                   return_value=timestamp):
                tp.process_metrics(metrics)
        alarms = tp.process_alarms()
        self.assertEqual(1, len(alarms))
        self.assertEqual('ALARM', json.loads(alarms[0])['state'])
        ad = self.util.get_alarm_def("alarm_def_periods")
        tp = processor.ThresholdProcessor(ad)
        metrics_list = self.util.get_metrics("metrics_periods_2")
        for metrics in metrics_list:
            timestamp = json.loads(metrics)['timestamp']
            with mock.patch.object(tu, 'utcnow_ts',
                                   return_value=timestamp):
                tp.process_metrics(metrics)
        alarms = tp.process_alarms()
        self.assertEqual(0, len(alarms))

        # test alarms with match_up
        ad = self.util.get_alarm_def("alarm_def_match_by")
        tp = processor.ThresholdProcessor(ad)
        metrics_list = self.util.get_metrics("metrics_match_by")
        for metrics in metrics_list:
            timestamp = json.loads(metrics)['timestamp']
            with mock.patch.object(tu, 'utcnow_ts',
                                   return_value=timestamp):
                tp.process_metrics(metrics)
        alarms = tp.process_alarms()
        self.assertEqual(3, len(alarms))
        self.assertEqual('ALARM', tp.expr_data_queue['h1,']['state'])
        self.assertEqual('ALARM', tp.expr_data_queue['h2,']['state'])
        self.assertEqual('OK', tp.expr_data_queue['h3,']['state'])

        # test alarms with multiple match_ups
        ad = self.util.get_alarm_def("alarm_def_multi_match_by")
        tp = processor.ThresholdProcessor(ad)
        metrics_list = self.util.get_metrics("metrics_multi_match_by")
        for metrics in metrics_list:
            timestamp = json.loads(metrics)['timestamp']
            with mock.patch.object(tu, 'utcnow_ts',
                                   return_value=timestamp):
                tp.process_metrics(metrics)
        alarms = tp.process_alarms()
        self.assertEqual(3, len(alarms))

        # test alarms with func count
        ad = self.util.get_alarm_def("alarm_def_count")
        tp = processor.ThresholdProcessor(ad)
        metrics_list = self.util.get_metrics("metrics_count_ok")
        for metrics in metrics_list:
            timestamp = json.loads(metrics)['timestamp']
            with mock.patch.object(tu, 'utcnow_ts',
                                   return_value=timestamp):
                tp.process_metrics(metrics)
        alarms = tp.process_alarms()
        self.assertEqual(1, len(alarms))
        self.assertEqual('OK', json.loads(alarms[0])['state'])
        metrics_list = self.util.get_metrics("metrics_count_alarm")
        for metrics in metrics_list:
            timestamp = json.loads(metrics)['timestamp']
            with mock.patch.object(tu, 'utcnow_ts',
                                   return_value=timestamp):
                tp.process_metrics(metrics)
        alarms = tp.process_alarms()
        self.assertEqual(1, len(alarms))
        self.assertEqual(1, len(json.loads(alarms[0])['metrics']))
        self.assertEqual('ALARM', json.loads(alarms[0])['state'])

        # test alarms with metrics having more dimensions
        ad = self.util.get_alarm_def("alarm_def_more_dimensions")
        tp = processor.ThresholdProcessor(ad)
        metrics_list = self.util.get_metrics("metrics_more_dimensions")
        for metrics in metrics_list:
            timestamp = json.loads(metrics)['timestamp']
            with mock.patch.object(tu, 'utcnow_ts',
                                   return_value=timestamp):
                tp.process_metrics(metrics)
        alarms = tp.process_alarms()
        self.assertEqual(1, len(alarms))
        self.assertEqual(1, len(json.loads(alarms[0])['metrics']))
        self.assertEqual('ALARM', json.loads(alarms[0])['state'])

        # test when receiving wrong format metrics
        ad = self.util.get_alarm_def("alarm_def_match_by")
        tp = processor.ThresholdProcessor(ad)
        metrics_list = self.util.get_metrics("metrics_match_by_wrong")
        for metrics in metrics_list:
            timestamp = json.loads(metrics)['timestamp']
            with mock.patch.object(tu, 'utcnow_ts',
                                   return_value=timestamp):
                tp.process_metrics(metrics)
        alarms = tp.process_alarms()
        self.assertEqual(1, len(alarms))
        self.assertEqual([1300],
                         json.loads(alarms[0])
                         ['sub_alarms'][0]['current_values'])

        # test when received metrics dimension not match
        ad = self.util.get_alarm_def("alarm_def_match_by")
        tp = processor.ThresholdProcessor(ad)
        alarms = tp.process_alarms()
        metrics_list = self.util.get_metrics("metrics_not_match")
        for metrics in metrics_list:
            tp.process_metrics(metrics)
        alarms = tp.process_alarms()
        self.assertEqual('OK', json.loads(alarms[0])['state'])

        # test a success update alarm definition
        ad = self.util.get_alarm_def("alarm_def_match_by")
        tp = processor.ThresholdProcessor(ad)
        metrics_list = self.util.get_metrics("metrics_match_by")
        for metrics in metrics_list:
            timestamp = json.loads(metrics)['timestamp']
            with mock.patch.object(tu, 'utcnow_ts',
                                   return_value=timestamp):
                tp.process_metrics(metrics)
        alarms = tp.process_alarms()
        ad = self.util.get_alarm_def("alarm_def_match_by_update")
        re = tp.update_thresh_processor(ad)
        self.assertTrue(re)
        alarms = tp.process_alarms()
        self.assertEqual(3, len(alarms))
        ad = self.util.get_alarm_def("alarm_def_periods")
        tp = processor.ThresholdProcessor(ad)
        ad = self.util.get_alarm_def("alarm_def_periods_update")
        re = tp.update_thresh_processor(ad)
        self.assertTrue(re)
