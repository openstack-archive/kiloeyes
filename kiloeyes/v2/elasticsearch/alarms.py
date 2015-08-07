# Copyright 2015 Carnegie Mellon University
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


import ast
import falcon
from oslo_config import cfg
from stevedore import driver

from kiloeyes.common import es_conn
from kiloeyes.common import namespace
from kiloeyes.common import resource_api
from kiloeyes.openstack.common import log


try:
    import ujson as json
except ImportError:
    import json

alarms_opts = [
    cfg.StrOpt('doc_type', default='alarms',
               help='The doc_type that alarm definitions will be saved to.'),
    cfg.StrOpt('index_strategy', default='timed',
               help='The index strategy used to create index name.'),
    cfg.StrOpt('index_prefix', default='data_',
               help='The index prefix where metrics were saved to.'),
    cfg.IntOpt('size', default=10000,
               help=('The query result limit. Any result set more than '
                     'the limit will be discarded.')),
]

cfg.CONF.register_opts(alarms_opts, group='alarms')

LOG = log.getLogger(__name__)


class AlarmDispatcher(object):

    def __init__(self, global_conf):
        LOG.debug('Initializing Alarm V2API!')
        super(AlarmDispatcher, self).__init__()
        self.doc_type = cfg.CONF.alarms.doc_type
        self.index_prefix = cfg.CONF.alarms.index_prefix
        self.size = cfg.CONF.alarms.size

        # load index strategy
        if cfg.CONF.alarms.index_strategy:
            self.index_strategy = driver.DriverManager(
                namespace.STRATEGY_NS,
                cfg.CONF.alarms.index_strategy,
                invoke_on_load=True,
                invoke_kwds={}).driver
            LOG.debug(self.index_strategy)
        else:
            self.index_strategy = None

        self._es_conn = es_conn.ESConnection(
            self.doc_type, self.index_strategy, self.index_prefix)

    def _get_alarms_response(self, res, ele_name='hits'):
        if res and res.status_code == 200:
            obj = res.json()
            if obj:
                return obj.get(ele_name)
            return None
        else:
            return None

    @resource_api.Restify('/v2.0/alarms', method='get')
    def do_get_alarms(self, req, res):
        LOG.debug('The alarms GET request is received!')

        # Extract the query string frm the request
        query_string = req.query_string
        LOG.debug('Request Query String: %s' % query_string)

        # Transform the query string with proper search format
        # params = self._get_alarms_helper(query_string)
        # LOG.debug('Query Data: %s' % params)
        params = ('{"aggs": {"latest_state": {'
                  '"terms": {"field": "alarm_definition.name", "size": 0},'
                  '"aggs": {"top_state_hits": {"top_hits": {"sort": ['
                  '{"updated_timestamp": {"order": "desc"}}],'
                  '"_source": {"include": ['
                  '"state", "created_timestamp","updated_timestamp",'
                  '"metrics","sub_alarms","state_updated_timestamp",'
                  '"id", "alarm_definition"]},"size" : 1}}}}}}')

        es_res = self._es_conn.get_messages(json.loads(params),
                                            q_string='search_type=count')
        res.status = getattr(falcon, 'HTTP_%s' % es_res.status_code)
        LOG.debug('Query to ElasticSearch returned Status: %s' %
                  es_res.status_code)

        es_res = self._get_alarms_response(es_res, ele_name='aggregations')
        LOG.debug('Query to ElasticSearch returned: %s' % es_res)

        res.body = ''
        result_elements = []
        try:
            if es_res["latest_state"]:
                res_data = es_res["latest_state"]["buckets"]
                res.body = '['
                for bucket in res_data:
                    alarm = bucket['top_state_hits']['hits']['hits'][0]
                    if alarm and alarm['_source']:
                        alarm = alarm['_source']
                        result_elements.append({
                            "id": alarm["id"],
                            "links": [{"rel": "self",
                                       "href": req.uri}],
                            "alarm_definition": alarm["alarm_definition"],
                            "metrics": alarm["metrics"],
                            "state": alarm["state"],
                            "sub_alarms": alarm["sub_alarms"],
                            "state_updated_timestamp":
                                alarm["state_updated_timestamp"],
                            "updated_timestamp": alarm["updated_timestamp"],
                            "created_timestamp": alarm["created_timestamp"]})
                res.body = json.dumps({
                    "links": [{"rel": "self", "href": req.uri}],
                    "elements": result_elements
                })
            else:
                res.body = ''
            res.content_type = 'application/json;charset=utf-8'
        except Exception:
            res.status = getattr(falcon, 'HTTP_400')
            LOG.exception('Error occurred while handling Alarms Get Request.')

    @resource_api.Restify('/v2.0/alarms/{id}', method='get')
    def do_get_alarms_by_id(self, req, res, id):
        LOG.debug('The alarms by id GET request is received!')
        LOG.debug(id)

        es_res = self._es_conn.get_message_by_id(id)
        res.status = getattr(falcon, 'HTTP_%s' % es_res.status_code)
        LOG.debug('Query to ElasticSearch returned Status: %s' %
                  es_res.status_code)

        es_res = self._get_alarms_response(es_res)
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
                        "metrics": res_data["_source"]["metrics"],
                        "state": res_data["_source"]["state"],
                        "sub_alarms": res_data["_source"]["sub_alarms"],
                        "state_updated_timestamp":
                            res_data["_source"]["state_updated_timestamp"],
                        "updated_timestamp":
                            res_data["_source"]["updated_timestamp"],
                        "created_timestamp":
                            res_data["_source"]["created_timestamp"]})

                    res.content_type = 'application/json;charset=utf-8'
            else:
                res.body = ''
        except Exception:
            res.status = getattr(falcon, 'HTTP_400')
            LOG.exception('Error occurred while handling Alarm '
                          'Get By ID Request.')

    @resource_api.Restify('/v2.0/alarms/{id}', method='put')
    def do_put_alarms(self, req, res, id):
        LOG.debug("Put the alarm with id: %s" % id)
        try:
            msg = req.stream.read()
            put_msg = ast.literal_eval(msg)
            es_res = self._es_conn.put_messages(json.dumps(put_msg), id)
            LOG.debug('Query to ElasticSearch returned Status: %s' %
                      es_res)
            res.status = getattr(falcon, 'HTTP_%s' % es_res)
        except Exception:
            res.status = getattr(falcon, 'HTTP_400')
            LOG.exception('Error occurred while handling Alarm Put Request.')

    @resource_api.Restify('/v2.0/alarms/{id}', method='delete')
    def do_delete_alarms(self, req, res, id):
        LOG.debug("Delete the alarm with id: %s" % id)
        try:
            es_res = self._es_conn.del_messages(id)
            LOG.debug('Query to ElasticSearch returned Status: %s' %
                      es_res)
            res.status = getattr(falcon, 'HTTP_%s' % es_res)
        except Exception:
            res.status = getattr(falcon, 'HTTP_400')
            LOG.exception('Error occurred while handling '
                          'Alarm Delete Request.')
