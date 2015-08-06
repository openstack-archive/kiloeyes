# Copyright 2015 Carnegie Mellon University
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

import ast
import falcon
import json
from oslo_config import cfg
import re
from stevedore import driver
import uuid

from kiloeyes.common import es_conn
from kiloeyes.common import namespace
from kiloeyes.common import resource_api
from kiloeyes.openstack.common import log


NOTIFICATION_METHOD_OPTS = [
    cfg.StrOpt('doc_type', default='notificationmethods',
               help='The doc type that notification_methods '
                    'will be saved into.'),
    cfg.StrOpt('index_strategy', default='fixed',
               help='The index strategy used to create index name.'),
    cfg.StrOpt('index_prefix', default='data_',
               help='The index prefix where metrics were saved to.'),
    cfg.IntOpt('size', default=10000,
               help=('The query result limit. Any result set more than '
                     'the limit will be discarded. To see all the matching '
                     'result, narrow your search by using a small time '
                     'window or strong matching name')),
]

cfg.CONF.register_opts(NOTIFICATION_METHOD_OPTS, group="notificationmethods")

LOG = log.getLogger(__name__)


class ParamUtil(object):

    @staticmethod
    def validateEmail(addr):
        if len(addr) > 7:
            if (re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\."
                         "([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", addr)
                    is not None):
                return True
        return False

    @staticmethod
    def name(req):
        # parse name from request
        name = req.get_param('name')

        if name and name.strip():
            return name
        else:
            return "DefaultNotificationMethods"

    @staticmethod
    def type_address(req):
        # parse notification type from request
        # Default is EMAIL
        type = req.get_param('type')
        address = req.get_param('address')

        # Currently, notification method types of email,
        # PagerDuty and webhooks are supported.
        # In the case of email, the address is the email address.
        # For PagerDuty, the address is the PagerDuty Service API Key.
        # For webhook, the address is the URL of the webhook.
        if (type and type.strip() == 'EMAIL'
                and address and address.strip()
                and ParamUtil.validateEmail(address.strip())):
            return ("EMAIL", address.strip())
        elif (type and type.strip() == 'PAGEDUTY'
                and address and address.strip()):
            return ("PAGEDUTY", address.strip())
        elif (type and type.strip() == 'WEBHOOK'
                and address and address.strip()):
            return ("WEBHOOK", address.strip())
        else:
            return None


class NotificationMethodDispatcher(object):

    def __init__(self, global_conf):
        LOG.debug('initializing V2API in NotificationMethodDispatcher!')
        super(NotificationMethodDispatcher, self).__init__()
        self.doc_type = cfg.CONF.notificationmethods.doc_type
        self.size = cfg.CONF.notificationmethods.size

        # load index strategy
        if cfg.CONF.notificationmethods.index_strategy:
            self.index_strategy = driver.DriverManager(
                namespace.STRATEGY_NS,
                cfg.CONF.notificationmethods.index_strategy,
                invoke_on_load=True,
                invoke_kwds={}).driver
            LOG.debug(dir(self.index_strategy))
        else:
            self.index_strategy = None

        self.index_prefix = cfg.CONF.notificationmethods.index_prefix

        self._es_conn = es_conn.ESConnection(
            self.doc_type, self.index_strategy, self.index_prefix)

    def post_data(self, req, res):
        LOG.debug('In NotificationMethodDispatcher::post_data.')
        msg = req.stream.read()
        # convert msg to dict
        dict_msg = ast.literal_eval(msg)

        # random uuid used for store the methods in database
        id = str(uuid.uuid4())

        # add an id to store in elasticsearch
        dict_msg["id"] = id

        # add an item "request" in the msg to tell
        # the receiver this is a POST request
        # The final msg is something like:
        # {"id":"c60ec47e-5038-4bf1-9f95-4046c6e9a759",
        # "request":"POST",
        # "name":"TheName",
        # "type":"TheType",
        # "Address":"TheAddress"}
        dict_msg["request"] = "POST"

        LOG.debug("post notification method: %s" % dict_msg)
        code = self.handle_notification_msg(dict_msg)
        res.status = getattr(falcon, 'HTTP_' + str(code))

    def put_data(self, req, res, id):
        LOG.debug('In NotificationMethodDispatcher::put_data.')
        msg = req.stream.read()

        dict_msg = ast.literal_eval(msg)

        # specify the id to match in elasticsearch for update
        dict_msg["id"] = id

        # add an item "request" in the msg to tell the receiver this is a PUT
        # request
        dict_msg["request"] = "PUT"

        LOG.debug("put notification method: %s" % dict_msg)
        code = self.handle_notification_msg(dict_msg)
        res.status = getattr(falcon, 'HTTP_' + str(code))

    def del_data(self, req, res, id):
        LOG.debug('In NotificationMethodDispatcher::del_data.')

        dict_msg = {}

        # specify the id to match in elasticsearch for deletion
        dict_msg["id"] = id

        # add an item "request" in the msg to tell the receiver this is a DEL
        # request
        dict_msg["request"] = "DEL"

        LOG.debug("delete notification method: %s" % dict_msg)
        code = self.handle_notification_msg(dict_msg)
        res.status = getattr(falcon, 'HTTP_' + str(code))

    def _get_notification_method_response(self, res):
        if res and res.status_code == 200:
            obj = res.json()
            if obj:
                return obj.get('hits')
            return None
        else:
            return None

    def handle_notification_msg(self, dict_msg):
        # dict_msg's format is:
        # {"id":"c60ec47e-5038-4bf1-9f95-4046c6e9a759",
        # "request":"POST",
        # "name":"TheName",
        # "type":"TheType",
        # "Address":"TheAddress"}
        # We add the POS/PUT/DEL in the message to indicate the request
        # type

        # Get the notification id from the message,
        # this id will be used as _id for elasticsearch,
        # and also stored as id in the notification_methods document
        # type

        # convert to dict, pop request, and get id
        # after request is removed, the dict can be converted to
        # request body for elasticsearch
        request_type = dict_msg.pop("request", None)
        id = dict_msg["id"]

        if request_type is not None and id is not None:
            # post
            if request_type == 'POST':
                return self._es_conn.post_messages(json.dumps(dict_msg), id)

            # put
            if request_type == 'PUT':
                return self._es_conn.put_messages(json.dumps(dict_msg), id)

            # delete
            if request_type == 'DEL':
                return self._es_conn.del_messages(id)

    @resource_api.Restify('/v2.0/notification-methods/', method='get')
    def do_get_notification_methods(self, req, res):
        LOG.debug("The notification_methods GET request is received!")

        es_res = self._es_conn.get_messages({})
        res.status = getattr(falcon, 'HTTP_%s' % es_res.status_code)

        LOG.debug('Query to ElasticSearch returned: %s' % es_res.status_code)

        es_res = self._get_notification_method_response(es_res)
        LOG.debug('Query to ElasticSearch returned: %s' % es_res)

        res_data = es_res["hits"]
        if res_data:
            def _make_body(elements):
                yield '{"links": [{"rel": "self", "href":"'
                yield req.uri + '"}],'
                yield '"elements": ['
                first = True
                for element in elements:
                    if element['_source']:
                        if not first:
                            yield ','
                        else:
                            first = False
                        links = [{"rel": "self",
                                  "href": req.uri + "/" +
                                  element['_source']['id']}]
                        element['_source']['links'] = links
                        yield json.dumps(element['_source'])
                yield ']}'

            res.body = ''.join(_make_body(res_data))
        else:
            res.body = ''
        res.content_type = 'application/json;charset=utf-8'

    @resource_api.Restify('/v2.0/notification-methods/{id}', method='get')
    def do_get_notification_method_by_id(self, req, res, id):
        LOG.debug("The notification_methods GET by id request is received!")

        es_res = self._es_conn.get_message_by_id(id)
        res.status = getattr(falcon, 'HTTP_%s' % es_res.status_code)

        LOG.debug('Query to ElasticSearch returned: %s' % es_res.status_code)

        es_res = self._get_notification_method_response(es_res)
        LOG.debug('Query to ElasticSearch returned: %s' % es_res)

        if es_res and es_res.get('hits'):
            res_data = es_res['hits'][0]
            obj = res_data['_source']
            obj['id'] = id
            obj['links'] = [{"rel": "self",
                             "href": req.uri}]
            res.body = json.dumps(obj)
            res.content_type = 'application/json;charset=utf-8'
        else:
            res.body = ''

    @resource_api.Restify('/v2.0/notification-methods/', method='post')
    def do_post_notification_methods(self, req, res):
        self.post_data(req, res)

    @resource_api.Restify('/v2.0/notification-methods/{id}', method='put')
    def do_put_notification_methods(self, req, res, id):
        self.put_data(req, res, id)

    @resource_api.Restify('/v2.0/notification-methods/{id}', method='delete')
    def do_delete_notification_methods(self, req, res, id):
        self.del_data(req, res, id)
