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
from oslotest import base

from kiloeyes.v2.elasticsearch import versions

try:
    import ujson as json
except ImportError:
    import json


class TestVersionDispatcher(base.BaseTestCase):

    def setUp(self):
        super(TestVersionDispatcher, self).setUp()
        self.dispatcher = versions.VersionDispatcher({})

    def test_get_versions(self):
        req = mock.Mock()
        req.uri = 'http://fake'
        res = mock.Mock()
        self.dispatcher.get_versions(req, res)

        body = json.loads(res.body)
        self.assertEqual(body[0]['id'], 'v2.0')
        self.assertEqual(getattr(falcon, 'HTTP_200'), res.status)

    def test_get_version_by_id(self):
        req = mock.Mock()
        req.uri = 'http://fake'
        res = mock.Mock()
        self.dispatcher.get_version_by_id(req, res, 'v2.0')

        body = json.loads(res.body)
        self.assertEqual(body['id'], 'v2.0')
        self.assertEqual(getattr(falcon, 'HTTP_200'), res.status)
