# Copyright 2013 IBM Corp
##
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

from kiloeyes.common import resource_api
from oslo_log import log

LOG = log.getLogger(__name__)


# Ceilometer V2 API
class V2API(object):
    def __init__(self, global_conf):
        LOG.debug('initializing V2API!')
        self.global_conf = global_conf

    # Meter APIs
    @resource_api.Restify('/v2.0/meters', method='get')
    def get_meters(self, req, res):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/meters', method='post')
    def post_meters(self, req, res):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/meters/{meter_name}', method='get')
    def get_meter_byname(self, req, res, meter_name):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/meters/{meter_name}/statistics', method='get')
    def get_meter_statistics(self, req, res, meter_name):
        res.status = '501 Not Implemented'
