# Copyright 2016 Cornell University
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

from kiloeyes.middleware import keystone_augmenter
from oslotest import base

import StringIO

try:
        import ujson as json
except ImportError:
        import json


class TestKeystoneAugmenter(base.BaseTestCase):

        def setUp(self):
                super(TestKeystoneAugmenter, self).setUp()
                self.augmenter = keystone_augmenter.KeystoneAugmenter({}, {})

        # Tests keystone augmenter on a single metric
        def test_augment_metric(self):
                test_input = {
                    'name': 'test_metric',
                    'timestamp': 1234567890,
                    'dimensions': {'service': 'test_service'}
                }

                input_json = StringIO.StringIO(json.dumps(test_input))

                env = {
                    'wsgi.input': input_json,
                    'HTTP_X_TENANT': 'test',
                    'HTTP_X_TENANT_ID': 'testid',
                    'HTTP_X_USER': 'test_user',
                    'HTTP_USER_AGENT': 'kiloeyes-tester',
                    'HTTP_X_PROJECT_ID': 'projidtest',
                    'HTTP_X_USER_ID': 'testuid'
                }

                metric_expected = {
                    'name': 'test_metric',
                    'timestamp': 1234567890,
                    'dimensions': {'service': 'test_service'},
                    'tenant': 'test',
                    'tenant_id': 'testid',
                    'user': 'test_user',
                    'user_agent': 'kiloeyes-tester',
                    'project_id': 'projidtest',
                    'user_id': 'testuid'
                }

                augmented_env = self.augmenter.add_keystone_to_metrics(env)

                metric_res = json.loads(augmented_env['wsgi.input'].read())

                self.assertEqual(metric_expected, metric_res)

        # Tests keystone augmenter on a list of metrics
        def test_augment_list(self):
                test_input = [
                    {
                        'name': 'metric1',
                        'timestamp': 125213525352,
                        'dimensions': {'service': 'test_service'}
                    },
                    {
                        'name': 'metric2',
                        'timestamp': 135098109530,
                        'dimensions': {'service': 'test_service'}
                    }
                ]

                input_json = StringIO.StringIO(json.dumps(test_input))

                env = {
                    'wsgi.input': input_json,
                    'HTTP_X_TENANT': 'test',
                    'HTTP_X_TENANT_ID': 'testid1',
                    'HTTP_X_USER': 'test_user',
                    'HTTP_USER_AGENT': 'kiloeyes-tester',
                    'HTTP_X_PROJECT_ID': 'projidtest2',
                    'HTTP_X_USER_ID': 'testuid'
                }

                metrics_expected = [
                    {
                        'name': 'metric1',
                        'timestamp': 125213525352,
                        'dimensions': {'service': 'test_service'},
                        'tenant': 'test',
                        'tenant_id': 'testid1',
                        'user': 'test_user',
                        'user_agent': 'kiloeyes-tester',
                        'project_id': 'projidtest2',
                        'user_id': 'testuid'
                    },
                    {
                        'name': 'metric2',
                        'timestamp': 135098109530,
                        'dimensions': {'service': 'test_service'},
                        'tenant': 'test',
                        'tenant_id': 'testid1',
                        'user': 'test_user',
                        'user_agent': 'kiloeyes-tester',
                        'project_id': 'projidtest2',
                        'user_id': 'testuid'
                    }
                ]

                augmented_env = self.augmenter.add_keystone_to_metrics(env)

                metrics_res = json.loads(augmented_env['wsgi.input'].read())

                self.assertEqual(metrics_expected, metrics_res)
