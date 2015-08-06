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
from kiloeyes.openstack.common import log


LOG = log.getLogger(__name__)


class V2API(object):
    def __init__(self, global_conf):
        LOG.debug('initializing V2API!')
        self.global_conf = global_conf

    @resource_api.Restify('/', method='get')
    def do_get_versions(self, req, res, version_id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/{version_id}', method='get')
    def do_get_version_by_id(self, req, res, version_id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/metrics/', method='post')
    def do_post_metrics(self, req, res):
        res.status = '501 Not Implemented'

    # This is an extension to kiloeyes spec.
    @resource_api.Restify('/v2.0/metrics/{id}', method='get')
    def do_get_metrics_by_id(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/metrics/', method='get')
    def do_get_metrics(self, req, res):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/metrics/measurements', method='get')
    def do_get_measurements(self, req, res):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/metrics/names', method='get')
    def do_get_metrics_names(self, req, res):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/metrics/statistics')
    def do_get_statistics(self, req, res):
        res.status = '501 Not Implemented'

    # Notification-method APIs
    @resource_api.Restify('/v2.0/notification-methods', method='post')
    def do_post_notification_methods(self, req, res):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/notification-methods/', method='get')
    def do_get_notification_methods(self, req, res):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/notification-methods/{id}', method='get')
    def do_get_notification_method_by_id(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/notification-methods/{id}', method='put')
    def do_put_notification_methods(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/notification-methods/{id}', method='delete')
    def do_delete_notification_methods(self, req, res, id):
        res.status = '501 Not Implemented'

    # Alarm-definition APIs
    @resource_api.Restify('/v2.0/alarm-definitions/', method='post')
    def do_post_alarm_definitions(self, req, res):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/alarm-definitions/', method='get')
    def do_get_alarm_definitions(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/alarm-definitions/{id}', method='get')
    def do_get_alarm_definition_by_id(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/alarm-definitions/{id}', method='put')
    def do_put_alarm_definition_by_id(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/alarm-definitions/{id}', method='patch')
    def do_patch_alarm_definition_by_id(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/alarm-definitions/{id}', method='delete')
    def do_delete_alarm_definition_by_id(self, req, res, id):
        res.status = '501 Not Implemented'

    # Alarm APIs
    @resource_api.Restify('/v2.0/alarms/', method='get')
    def do_get_alarms(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/alarms/state-history', method='get')
    def do_get_alarms_state_history(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/alarms/{alarm_id}', method='get')
    def do_get_alarm_by_id(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/alarms/{alarm_id}', method='put')
    def do_put_alarms(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/alarms/{alarm_id}', method='patch')
    def do_patch_alarms(self, req, res, id):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/alarms/{alarm_id}', method='delete')
    def do_delete_alarms(self, req, res, id):
        res.status = '501 Not Implemented'

    # This is an extention to the API spec.
    @resource_api.Restify('/v2.0/alarms', method='post')
    def do_post_alarms(self, req, res):
        res.status = '501 Not Implemented'

    @resource_api.Restify('/v2.0/alarms/{alarm_id}/state-history')
    def do_get_alarm_state_history(self, req, res, id):
        res.status = '501 Not Implemented'
