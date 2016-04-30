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
from kiloeyes.common import timeutils as tu
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

        self._oldsample_agg = """
        {"by_name":{"terms":{"field":"name","size":%(size)d},
        "aggs":{"by_dim":{"terms":{"field":"dimensions_hash","size":%(size)d},
        "aggs":{"meters":{"top_hits":{"_source":{"exclude":
        ["dimensions_hash"]},"size":1}}}}}}}
        """

        self._meter_stats_agg = """
        {"by_name":{"terms":{"field":"name","size":%(size)d},
        "aggs":{"by_dim":{"terms":{"field":"dimensions_hash",
        "size":%(size)d},"aggs":{"dimension":{"top_hits":{"_source":
        {"exclude":["dimensions_hash","timestamp","value"]},"size":1}},
        "periods":{"date_histogram":{"field":"timestamp",
        "interval":"%(period)s"},"aggs":{"statistics":{"stats":
        {"field":"value"}}}}}}}}}
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
        LOG.debug('Getting the call.')
        msg = req.stream.read()
        LOG.debug('@$Post Message is %s' % msg)

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
    def get_meters(self, req, res):
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

    @resource_api.Restify('/v2.0/meters', method='post')
    def post_meters(self, req, res):
        self.post_data(req, res)

    @resource_api.Restify('/v2.0/meters/{meter_name}', method='get')
    def get_meter_byname(self, req, res, meter_name):
        LOG.debug('The meter %s sample GET request is received' % meter_name)

        # process query condition
        query = []
        metrics.ParamUtil.common(req, query)
        _meter_ag = self._oldsample_agg % {"size": self.size}
        if query:
            body = ('{"query":{"bool":{"must":' + json.dumps(query) + '}},'
                    '"size":' + str(self.size) + ','
                    '"aggs":' + _meter_ag + '}')
        else:
            body = '{"aggs":' + _meter_ag + '}'

        # modify the query url to filter out name
        query_url = []
        if meter_name:
            query_url = self._query_url + '&q=name:' + meter_name
        else:
            query_url = self._query_url
        LOG.debug('Request body:' + body)
        LOG.debug('Request url:' + query_url)
        es_res = requests.post(query_url, data=body)
        res.status = getattr(falcon, 'HTTP_%s' % es_res.status_code)

        LOG.debug('Query to ElasticSearch returned: %s' % es_res.status_code)
        res_data = self._get_agg_response(es_res)
        LOG.debug('@$Result data is %s\n' % res_data)
        if res_data:
            # convert the response into ceilometer meter OldSample format
            aggs = res_data['by_name']['buckets']
            flag = {'is_first': True}

            def _render_hits(item):
                _type = item['meters']['hits']['hits'][0]['_type']
                _source = item['meters']['hits']['hits'][0]['_source']
                rslt = ('{"counter_name":' + json.dumps(_source['name']) + ','
                        '"counter_type":' + json.dumps(_type) + ','
                        '"counter_unit":null,'
                        '"counter_volume":' +
                        json.dumps(_source['value']) + ','
                        '"message_id":null,'
                        '"project_id":' +
                        json.dumps(_source['project_id']) + ','
                        '"recorded_at":null,'
                        '"resource_id":' +
                        json.dumps(_source['tenant_id']) + ','
                        '"resource_metadata":null,'
                        '"source":' + json.dumps(_source['user_agent']) + ','
                        '"timestamp":' + json.dumps(_source['timestamp']) + ','
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

    @resource_api.Restify('/v2.0/meters/{meter_name}/statistics', method='get')
    def get_meter_statistics(self, req, res, meter_name):
        LOG.debug('The meter %s statistics GET request is received' %
                  meter_name)
        # process query conditions
        query = []
        metrics.ParamUtil.common(req, query)
        period = metrics.ParamUtil.period(req)

        _stats_ag = (self._meter_stats_agg %
                     {"size": self.size, "period": period})
        if query:
            body = ('{"query":{"bool":{"must":' + json.dumps(query) + '}},'
                    '"size":' + str(self.size) + ','
                    '"aggs":' + _stats_ag + '}')
        else:
            body = '{"aggs":' + _stats_ag + '}'

        # modify the query url to filter out name
        query_url = []
        if meter_name:
            query_url = self._query_url + '&q=name:' + meter_name
        else:
            query_url = self._query_url
        es_res = requests.post(query_url, data=body)
        res.status = getattr(falcon, 'HTTP_%s' % es_res.status_code)

        LOG.debug('Query to ElasticSearch returned: %s' % es_res.status_code)
        res_data = self._get_agg_response(es_res)
        if res_data:
            # convert the response into Ceilometer Statistics format
            aggs = res_data['by_name']['buckets']

            LOG.debug('@$Stats: %s' % json.dumps(aggs))

            def _render_stats(dim):
                is_first = True
                oldest_time = []
                previous_time = []
                for item in dim['periods']['buckets']:
                    current_time = item['key']
                    # calculte period and duration difference
                    if is_first:
                        period_diff = 'null'
                        oldest_time = current_time
                        duration_diff = 'null'
                        previous_time = current_time
                    else:
                        period_diff = (current_time - previous_time) / 1000
                        duration_diff = (current_time - oldest_time) / 1000
                    # parses the statistics data
                    _max = str(item['statistics']['max'])
                    _min = str(item['statistics']['min'])
                    _sum = str(item['statistics']['sum'])
                    _avg = str(item['statistics']['avg'])
                    _count = str(item['statistics']['count'])
                    curr_timestamp = tu.iso8601_from_timestamp(current_time)
                    prev_timestamp = tu.iso8601_from_timestamp(previous_time)
                    old_timestamp = tu.iso8601_from_timestamp(oldest_time)
                    rslt = ('{"avg":' + _avg + ','
                            '"count":' + _count + ','
                            '"duration":' + str(duration_diff) + ','
                            '"duration_end":' +
                            '"%s"' % str(curr_timestamp) + ','
                            '"duration_start":' +
                            '"%s"' % str(old_timestamp) + ','
                            '"max":' + _max + ','
                            '"min":' + _min + ','
                            '"period":' + str(period_diff) + ','
                            '"period_end":' +
                            '"%s"' % str(curr_timestamp) + ','
                            '"period_start":' +
                            '"%s"' % str(prev_timestamp) + ','
                            '"sum":' + _sum + ','
                            '"unit":null}')
                    previous_time = current_time
                    if is_first:
                        yield rslt
                        is_first = False
                    else:
                        yield ',' + rslt

            def _make_body(items):
                is_first = True
                yield '['
                for metric in items:
                    for dim in metric['by_dim']['buckets']:
                        if is_first:
                            is_first = False
                        else:
                            yield ','
                        for result in _render_stats(dim):
                            yield result
                yield ']'

            res.body = ''.join(_make_body(aggs))
            res.content_type = 'application/json;charset=utf-8'
        else:
            res.body = 'o'
