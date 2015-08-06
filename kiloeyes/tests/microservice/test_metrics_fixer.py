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
import time


from kiloeyes.microservice import metrics_fixer
from kiloeyes.openstack.common import log
from kiloeyes import tests

LOG = log.getLogger(__name__)


class TestMetricsFixer(tests.BaseTestCase):

    def setUp(self):
        super(TestMetricsFixer, self).setUp()

    def test__add_hash(self):
        item = {'name': 'name1', 'dimensions': {'name1': 'value1'},
                'timestamp': time.time()}
        result = metrics_fixer.MetricsFixer._add_hash(item)
        data = json.loads(result)
        self.assertTrue(data.get('dimensions_hash'))
        self.assertTrue(data['timestamp'])

        item = {'name': 'name1', 'timestamp': time.time()}
        result = metrics_fixer.MetricsFixer._add_hash(item)
        data = json.loads(result)
        self.assertFalse(data.get('dimensions_hash'))
        self.assertTrue(data['timestamp'])

    def test_process_msg_one(self):
        items = [{'name': 'name1', 'dimensions': {'name1': 'value1'},
                  'timestamp': time.time()}]
        fixer = metrics_fixer.MetricsFixer()
        result = fixer.process_msg(json.dumps(items))
        self.assertTrue(isinstance(result, str))
        self.assertTrue(result.startswith('{"index":{}}'))

    def test_process_msg_multiple(self):
        items = [{'name': 'name1', 'dimensions': {'name1': 'value1'},
                  'timestamp': time.time()}]
        items.append({'dimensions': {'p1': 1, 'p3': 100.12}})
        fixer = metrics_fixer.MetricsFixer()
        result = fixer.process_msg(json.dumps(items))
        self.assertTrue(isinstance(result, str))
