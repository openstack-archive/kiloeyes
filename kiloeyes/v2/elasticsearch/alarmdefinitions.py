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
from oslo_config import cfg
from stevedore import driver
import uuid

from kiloeyes.common import alarm_expr_parser
from kiloeyes.common import alarm_expr_validator
from kiloeyes.common import es_conn
from kiloeyes.common import namespace
from kiloeyes.common import resource_api
from kiloeyes.openstack.common import log


try:
    import ujson as json
except ImportError:
    import json


alarmdefinitions_opts = [
    cfg.StrOpt('doc_type', default='alarmdefinitions',
               help='The doc_type that alarm definitions will be saved to.'),
    cfg.StrOpt('index_strategy', default='fixed',
               help='The index strategy used to create index name.'),
    cfg.StrOpt('index_prefix', default='data_',
               help='The index prefix where metrics were saved to.'),
    cfg.IntOpt('size', default=1000,
               help=('The query result limit. Any result set more than '
                     'the limit will be discarded.')),
]


cfg.CONF.register_opts(alarmdefinitions_opts, group='alarmdefinitions')

STATES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

LOG = log.getLogger(__name__)


class AlarmDefinitionUtil(object):

    @staticmethod
    def severityparsing(msg):
        try:
            severity = msg["severity"]
            if severity in STATES:
                return msg
            else:
                msg["severity"] = "LOW"
                return msg

        except Exception:
            return msg


class AlarmDefinitionDispatcher(object):

    def __init__(self, global_conf):
        LOG.debug('Initializing AlarmDefinition V2API!')
        super(AlarmDefinitionDispatcher, self).__init__()
        self.doc_type = cfg.CONF.alarmdefinitions.doc_type
        self.size = cfg.CONF.alarmdefinitions.size

        # load index strategy
        if cfg.CONF.alarmdefinitions.index_strategy:
            self.index_strategy = driver.DriverManager(
                namespace.STRATEGY_NS,
                cfg.CONF.alarmdefinitions.index_strategy,
                invoke_on_load=True,
                invoke_kwds={}).driver
            LOG.debug(self.index_strategy)
        else:
            self.index_strategy = None

        self.index_prefix = cfg.CONF.alarmdefinitions.index_prefix

        self._es_conn = es_conn.ESConnection(
            self.doc_type, self.index_strategy, self.index_prefix)

    def _get_alarm_definitions_response(self, res):
        if res and res.status_code == 200:
            obj = res.json()
            if obj:
                return obj.get('hits')
        return None

    def _get_alarm_definitions_helper(self, query_string):
        query = {}
        queries = []
        field_string = 'alarmdefinitions.expression_data.dimensions.'
        if query_string:
            params = query_string.split('&')
            for current_param in params:
                current_param_split = current_param.split('=')
                if current_param_split[0] == 'dimensions':
                    current_dimension_split = (
                        current_param_split[1].split(','))
                    for current_dimension in current_dimension_split:
                        current_dimen_data = current_dimension.split(':')
                        queries.append({
                            'query_string': {
                                'default_field': (field_string +
                                                  current_dimen_data[0]),
                                'query': current_dimen_data[1]
                            }
                        })
                elif current_param_split[0] in ['limit', 'offset']:
                    # ignore the limit and offset for now.
                    pass
                else:
                    queries.append({
                        'query_string': {
                            'default_field': current_param_split[0],
                            'query': current_param_split[1]
                        }
                    })
            LOG.debug(queries)
            query = {
                'query': {
                    'bool': {
                        'must': queries
                    }
                }
            }

        LOG.debug('Parsed Query: %s' % query)
        return query

    @resource_api.Restify('/v2.0/alarm-definitions/', method='post')
    def do_post_alarm_definitions(self, req, res):
        LOG.debug('Creating the alarm definitions')
        msg = req.stream.read()
        LOG.debug("Message: %s" % msg)
        post_msg = ast.literal_eval(msg)

        # random uuid generation for alarm definition
        id = str(uuid.uuid4())
        post_msg["id"] = id
        post_msg = AlarmDefinitionUtil.severityparsing(post_msg)
        post_msg_json = json.dumps(post_msg)
        LOG.debug("Validating Alarm Definition Data: %s" % post_msg_json)

        if alarm_expr_validator.is_valid_alarm_definition(post_msg_json):
            LOG.debug("Post Alarm Definition method: %s" % post_msg)
            try:
                expression_parsed = (
                    alarm_expr_parser.AlarmExprParser(post_msg["expression"]))
                expression_data = expression_parsed.sub_alarm_expressions
                expression_data_list = []
                for temp in expression_data:
                    expression_data_list.append(expression_data[temp])
                post_msg["expression_data"] = expression_data_list
                LOG.debug(post_msg)

                es_res = self._es_conn.post_messages(json.dumps(post_msg), id)
                LOG.debug('Query to ElasticSearch returned Status: %s' %
                          es_res)
                res.status = getattr(falcon, 'HTTP_%s' % es_res)
            except Exception:
                LOG.exception('Error occurred while handling '
                              'Alarm Definition Post Request.')
                res.status = getattr(falcon, 'HTTP_400')
        else:
            LOG.error('Alarm definition is not valid.')
            res.status = getattr(falcon, 'HTTP_400')

    @resource_api.Restify('/v2.0/alarm-definitions/{id}', method='get')
    def do_get_alarm_definitions_by_id(self, req, res, id):
        LOG.debug('The alarm definitions GET request is received!')
        LOG.debug(id)

        es_res = self._es_conn.get_message_by_id(id)
        res.status = getattr(falcon, 'HTTP_%s' % es_res.status_code)

        LOG.debug('Query to ElasticSearch returned Status: %s' %
                  es_res.status_code)
        es_res = self._get_alarm_definitions_response(es_res)
        LOG.debug('Query to ElasticSearch returned: %s' % es_res)

        res.body = ''
        try:
            if es_res["hits"]:
                res_data = es_res["hits"][0]
                if res_data:
                    res.body = json.dumps({
                        "id": id,
                        "links": [{"rel": "self",
                                   "href": req.uri}],
                        "name": res_data["_source"]["name"],
                        "description": res_data["_source"]["description"],
                        "expression": res_data["_source"]["expression"],
                        "expression_data":
                            res_data["_source"]["expression_data"],
                        "severity": res_data["_source"]["severity"],
                        "match_by": res_data["_source"]["match_by"],
                        "alarm_actions": res_data["_source"]["alarm_actions"],
                        "ok_actions": res_data["_source"]["ok_actions"],
                        "undetermined_actions": res_data["_source"]
                        ["undetermined_actions"]})
                    res.content_type = 'application/json;charset=utf-8'
        except Exception:
            LOG.exception('Error occurred while handling Alarm Definition '
                          'Get Request.')

    @resource_api.Restify('/v2.0/alarm-definitions/{id}', method='put')
    def do_put_alarm_definitions(self, req, res, id):
        LOG.debug("Put the alarm definitions with id: %s" % id)

        es_res = self._es_conn.get_message_by_id(id)
        LOG.debug('Query to ElasticSearch returned Status: %s' %
                  es_res.status_code)
        es_res = self._get_alarm_definitions_response(es_res)
        LOG.debug('Query to ElasticSearch returned: %s' % es_res)

        original_data = {}
        try:
            if es_res["hits"]:
                res_data = es_res["hits"][0]
                if res_data:
                    original_data = json.dumps({
                        "id": id,
                        "name": res_data["_source"]["name"],
                        "description": res_data["_source"]["description"],
                        "expression": res_data["_source"]["expression"],
                        "expression_data":
                            res_data["_source"]["expression_data"],
                        "severity": res_data["_source"]["severity"],
                        "match_by": res_data["_source"]["match_by"],
                        "alarm_actions": res_data["_source"]["alarm_actions"],
                        "ok_actions": res_data["_source"]["ok_actions"],
                        "undetermined_actions": res_data["_source"]
                        ["undetermined_actions"]})

            msg = req.stream.read()
            put_msg = ast.literal_eval(msg)
            put_msg = AlarmDefinitionUtil.severityparsing(put_msg)

            expression_parsed = (
                alarm_expr_parser.AlarmExprParser(put_msg["expression"])
            )
            expression_data = expression_parsed.sub_alarm_expressions
            expression_data_list = []
            for temp in expression_data:
                expression_data_list.append(expression_data[temp])
            put_msg["expression_data"] = expression_data_list

            put_msg_json = json.dumps(put_msg)
            LOG.debug("Alarm Definition Put Data: %s" % put_msg_json)

            if alarm_expr_validator.is_valid_update_alarm_definition(
                    original_data, put_msg_json):
                es_res = self._es_conn.put_messages(put_msg_json, id)
                LOG.debug('Query to ElasticSearch returned Status: %s' %
                          es_res)
                res.status = getattr(falcon, 'HTTP_%s' % es_res)
            else:
                res.status = getattr(falcon, 'HTTP_400')
                LOG.debug("Validating Alarm Definition Failed !!")
        except Exception:
            res.status = getattr(falcon, 'HTTP_400')
            LOG.exception('Error occurred while handling Alarm '
                          'Definition Put Request.')

    @resource_api.Restify('/v2.0/alarm-definitions/{id}', method='delete')
    def do_delete_alarm_definitions(self, req, res, id):
        LOG.debug("Delete the alarm definitions with id: %s" % id)
        try:
            es_res = self._es_conn.del_messages(id)
            LOG.debug('Query to ElasticSearch returned Status: %s' %
                      es_res)
            res.status = getattr(falcon, 'HTTP_%s' % es_res)
        except Exception:
            res.status = getattr(falcon, 'HTTP_400')
            LOG.exception('Error occurred while handling Alarm '
                          'Definition Delete Request.')

    @resource_api.Restify('/v2.0/alarm-definitions/', method='get')
    def do_get_alarm_definitions_filtered(self, req, res):
        LOG.debug('The alarm definitions GET request is received!')

        query_string = req.query_string
        LOG.debug('Request Query String: %s' % query_string)

        params = self._get_alarm_definitions_helper(query_string)
        LOG.debug('Query Data: %s' % params)

        es_res = self._es_conn.get_messages(params)
        res.status = getattr(falcon, 'HTTP_%s' % es_res.status_code)
        LOG.debug('Query to ElasticSearch returned Status: %s' %
                  es_res.status_code)

        es_res = self._get_alarm_definitions_response(es_res)
        LOG.debug('Query to ElasticSearch returned: %s' % es_res)

        res.body = ''
        result_elements = []
        try:
            if es_res["hits"]:
                res_data = es_res["hits"]
                for current_alarm in res_data:
                    if current_alarm:
                        result_elements.append({
                            "id": current_alarm["_source"]["id"],
                            "links": [{"rel": "self",
                                       "href": req.uri}],
                            "name": current_alarm["_source"]["name"],
                            "description":
                                current_alarm["_source"]["description"],
                            "expression":
                                current_alarm["_source"]["expression"],
                            "expression_data":
                                current_alarm["_source"]["expression_data"],
                            "severity":
                                current_alarm["_source"]["severity"],
                            "match_by":
                                current_alarm["_source"]["match_by"],
                            "alarm_actions":
                                current_alarm["_source"]["alarm_actions"],
                            "ok_actions":
                                current_alarm["_source"]["ok_actions"],
                            "undetermined_actions":
                                current_alarm["_source"]
                            ["undetermined_actions"]})

                res.body = json.dumps({
                    "links": [{"rel": "self", "href": req.uri}],
                    "elements": result_elements
                })
            else:
                res.body = ""
            res.content_type = 'application/json;charset=utf-8'
        except Exception:
            res.status = getattr(falcon, 'HTTP_400')
            LOG.exception('Error occurred while handling Alarm '
                          'Definitions Get Request.')
