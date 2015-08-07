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

import datetime
import falcon

from kiloeyes.common import resource_api
from kiloeyes.openstack.common import log

try:
    import ujson as json
except ImportError:
    import json

LOG = log.getLogger(__name__)

UPDATED = str(datetime.datetime(2014, 1, 1, 0, 0, 0))


class VersionDispatcher(object):
    def __init__(self, global_conf):
        LOG.debug('initializing V2API!')
        super(VersionDispatcher, self).__init__()

    @resource_api.Restify('/', method='get')
    def get_versions(self, req, res):
        res.body = json.dumps([{
            "id": "v2.0",
            "links": [{"rel": "self",
                       "href": req.uri}],
            "status": "CURRENT",
            "updated": UPDATED}])
        res.status = getattr(falcon, 'HTTP_200')

    @resource_api.Restify('/{version_id}', method='get')
    def get_version_by_id(self, req, res, version_id):
        if version_id in ['v2.0', '2.0', '2']:
            res.body = json.dumps({
                "id": "v2.0",
                "links": [{"rel": "self",
                           "href": req.uri}],
                "status": "CURRENT",
                "updated": UPDATED})
            res.status = getattr(falcon, 'HTTP_200')
        else:
            res.body = ''
            res.status = getattr(falcon, 'HTTP_501')
