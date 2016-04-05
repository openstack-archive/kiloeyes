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
from oslo_config import cfg
from oslo_log import log
import requests
from stevedore import driver

from kiloeyes.common import es_conn
from kiloeyes.common import kafka_conn
from kiloeyes.common import namespace
from kiloeyes.common import resource_api
from kiloeyes.v2.elasticsearch import metrics

try:
    import ujson as json
except ImportError:
    import json

METERS_OPTS = [
    cfg.StrOpt('topic', default='metrics',
               help='The topic that meters will be published to.'),
    cfg.StrOpt('doc_type', default='metrics',
               help='The doc type that meters will be saved into.'),
    cfg.StrOpt('index_strategy', default='fixed',
               help='The index strategy used to create index name.'),
    cfg.StrOpt('index_prefix', default='data_',
               help='The index prefix where meters were saved to.'),
    cfg.StrOpt('index_template', default='/etc/kiloeyes/metrics.template',
               help='The index template which meters index should use.'),
    cfg.IntOpt('size', default=10000,
               help=('The query result limit. Any result set more than '
                     'the limit will be discarded. To see all the matching '
                     'result, narrow your search by using a small time '
                     'window or strong matching name')),
]

cfg.CONF.register_opts(METERS_OPTS, group="meters")

LOG = log.getLogger(__name__)

UPDATED = str(datetime.datetime(2014, 1, 1, 0, 0, 0))


class MeterDispatcher(object):
    def __init__(self, global_conf):
        LOG.debug('initializing V2API!')
        super(MeterDispatcher, self).__init__()
        self.topic = cfg.CONF.meters.topic
        self.doc_type = cfg.CONF.meters.doc_type
        self.index_template = cfg.CONF.meters.index_template
        self.size = cfg.CONF.meters.size
        self._kafka_conn = kafka_conn.KafkaConnection(self.topic)

        # load index strategy
        if cfg.CONF.meters.index_strategy:
            self.index_strategy = driver.DriverManager(
                namespace.STRATEGY_NS,
                cfg.CONF.meters.index_strategy,
                invoke_on_load=True,
                invoke_kwds={}).driver
            LOG.debug(dir(self.index_strategy))
        else:
            self.index_strategy = None

        self.index_prefix = cfg.CONF.meters.index_prefix

        self._es_conn = es_conn.ESConnection(
            self.doc_type, self.index_strategy, self.index_prefix)

        # Setup the get meters query body pattern
        self._query_body = {
            "query": {"bool": {"must": []}},
            "size": self.size}

        self._aggs_body = {}
        self._stats_body = {}
        self._sort_clause = []

        # Setup the get meters query url, the url should be similar to this:
        # http://host:port/data_20141201/meters/_search
        # the url should be made of es_conn uri, the index prefix, meters
        # dispatcher topic, then add the key word _search.
        self._query_url = ''.join([self._es_conn.uri,
                                  self._es_conn.index_prefix, '*/',
                                  cfg.CONF.meters.topic,
                                  '/_search?search_type=count'])

        # Setup meters query aggregation command. To see the structure of
        # the aggregation, copy and paste it to a json formatter.
        self._meters_agg = """
        {"by_name":{"terms":{"field":"name","size":%(size)d},
        "aggs":{"by_dim":{"terms":{"field":"dimensions_hash","size":%(size)d},
        "aggs":{"meters":{"top_hits":{"_source":{"exclude":
        ["dimensions_hash","timestamp","value"]},"size":1}}}}}}}
        """

        self.setup_index_template()

    def setup_index_template(self):
        status = '400'
        with open(self.index_template) as template_file:
            template_path = ''.join([self._es_conn.uri,
                                     '/_template/metrics'])
            es_res = requests.put(template_path, data=template_file.read())
            status = getattr(falcon, 'HTTP_%s' % es_res.status_code)

        if status == '400':
            LOG.error('Metrics template can not be created. Status code %s'
                      % status)
            exit(1)
        else:
            LOG.debug('Index template set successfully! Status %s' % status)

    def post_data(self, req, res):
        msg = ""
        LOG.debug('@$Post Message is %s' % msg)
        LOG.debug('Getting the call.')
        msg = req.stream.read()

        code = self._kafka_conn.send_messages(msg)
        res.status = getattr(falcon, 'HTTP_' + str(code))

    def _get_agg_response(self, res):
        if res and res.status_code == 200:
            obj = res.json()
            if obj:
                return obj.get('aggregations')
            return None
        else:
            return None

    @resource_api.Restify('/v2.0/meters', method='get')
    def get_meter(self, req, res):
        LOG.debug('The meters GET request is received')

        # process query condition
        query = []
        metrics.ParamUtil.common(req, query)
        _meters_ag = self._meters_agg % {"size": self.size}
        if query:
            body = ('{"query":{"bool":{"must":' + json.dumps(query) + '}},'
                    '"size":' + str(self.size) + ','
                    '"aggs":' + _meters_ag + '}')
        else:
            body = '{"aggs":' + _meters_ag + '}'

        LOG.debug('Request body:' + body)
        LOG.debug('Request url:' + self._query_url)
        es_res = requests.post(self._query_url, data=body)
        res.status = getattr(falcon, 'HTTP_%s' % es_res.status_code)

        LOG.debug('Query to ElasticSearch returned: %s' % es_res.status_code)
        res_data = self._get_agg_response(es_res)
        if res_data:
            # convert the response into ceilometer meter format
            aggs = res_data['by_name']['buckets']
            flag = {'is_first': True}

            def _render_hits(item):
                _id = item['meters']['hits']['hits'][0]['_id']
                _type = item['meters']['hits']['hits'][0]['_type']
                _source = item['meters']['hits']['hits'][0]['_source']
                rslt = ('{"meter_id":' + json.dumps(_id) + ','
                        '"name":' + json.dumps(_source['name']) + ','
                        '"project_id":' +
                        json.dumps(_source['project_id']) + ','
                        '"resource_id":' +
                        json.dumps(_source['tenant_id']) + ','
                        '"source":' + json.dumps(_source['user_agent']) + ','
                        '"type":' + json.dumps(_type) + ','
                        '"unit":null,'
                        '"user_id":' + json.dumps(_source['user_id']) + '}')
                if flag['is_first']:
                    flag['is_first'] = False
                    return rslt
                else:
                    return ',' + rslt

            def _make_body(buckets):
                yield '['
                for by_name in buckets:
                    if by_name['by_dim']:
                        for by_dim in by_name['by_dim']['buckets']:
                            yield _render_hits(by_dim)
                yield ']'

            res.body = ''.join(_make_body(aggs))
            res.content_type = 'application/json;charset=utf-8'
        else:
            res.body = ''

    @resource_api.Restify('/v2.0/meters/', method='post')
    def post_meters(self, req, res):
        self.post_data(req, res)
