# Copyright 2015 Carnegie Mellon University
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from oslo_log import log
from stevedore import driver
import threading
import time

from kiloeyes.common import es_conn
from kiloeyes.common import kafka_conn
from kiloeyes.common import namespace
from kiloeyes.openstack.common import service as os_service

lock = threading.RLock()

THRESHOLD_ENGINE_OPTS = [
    cfg.StrOpt('metrics_topic',
               default='metrics',
               help='topics to read metrics'),
    cfg.StrOpt('alarm_topic',
               default='alarm',
               help='topic to send alarms'),
    cfg.StrOpt('processor',
               default='thresholding_processor',
               help='the thresh processor'),
    cfg.IntOpt('check_alarm_interval',
               default=60)
]
ALARM_DEFINITION_OPTS = [
    cfg.StrOpt('doc_type', default='alarmdefinitions',
               help='The doc_type that alarm definitions will be saved to.'),
    cfg.StrOpt('index_strategy', default='fixed',
               help='The index strategy used to create index name.'),
    cfg.StrOpt('index_prefix', default='data_',
               help='The index prefix where metrics were saved to.'),
    cfg.IntOpt('size', default=1000,
               help=('The query result limit. Any result set more than '
                     'the limit will be discarded.')),
    cfg.StrOpt('name', default='',
               help='The name for query alarm definitions.'),
    cfg.StrOpt('dimensions', default='',
               help='The dimensions for query alarm definitions.'),
    cfg.IntOpt('check_alarm_def_interval',
               default=120)
]


cfg.CONF.register_opts(THRESHOLD_ENGINE_OPTS, group="thresholdengine")
cfg.CONF.register_opts(ALARM_DEFINITION_OPTS, group="alarmdefinitions")

LOG = log.getLogger(__name__)


class AlarmPublisher(threading.Thread):
    """The thread to publish alarm messages.

    This class will periodically call processors to get alarms produced,
    and send them into kafka
    """
    def __init__(self, t_name, tp):
        threading.Thread.__init__(self, name=t_name)
        # init kafka connection to alarm topic
        self._publish_kafka_conn = None
        topic = cfg.CONF.thresholdengine.alarm_topic
        self._publish_kafka_conn = (
            kafka_conn.KafkaConnection(topic))
        # set time interval for calling processors to refresh alarms
        self.interval = cfg.CONF.thresholdengine.check_alarm_interval
        self.threshold_processors = tp

    def send_alarm(self):
        if self._publish_kafka_conn:
            if lock.acquire():
                for aid in self.threshold_processors:
                    # get alarms produced by each processor
                    for alarm in (self.threshold_processors
                                  [aid]['processor'].process_alarms()):
                        LOG.debug(alarm)
                        self._publish_kafka_conn.send_messages(alarm)
            lock.release()

    def run(self):
        while True:
            try:
                self.send_alarm()
                time.sleep(self.interval)
            except Exception:
                LOG.exception(
                    'Error occurred while publishing alarm messages.')

    def stop(self):
        self._publish_kafka_conn.close()


class MetricsConsumer(threading.Thread):
    """The thread to read metrics.

    This class will get metrics messages from kafka,
    and deliver them to processors.
    """
    def __init__(self, t_name, tp):
        threading.Thread.__init__(self, name=t_name)
        # init kafka connection to metrics topic
        self._consume_kafka_conn = None
        topic = cfg.CONF.thresholdengine.metrics_topic
        self._consume_kafka_conn = kafka_conn.KafkaConnection(topic)
        self.threshold_processors = tp

    def read_metrics(self):
        def consume_metrics():
            if lock.acquire():
                # send metrics to each processor
                for aid in self.threshold_processors:
                    processor = self.threshold_processors[aid]['processor']
                    processor.process_metrics(msg.message.value)
            lock.release()

        if self._consume_kafka_conn:
            for msg in self._consume_kafka_conn.get_messages():
                if msg and msg.message:
                    LOG.debug(msg.message.value)
                    consume_metrics()
            self._consume_kafka_conn.commit()

    def run(self):
        while True:
            try:
                self.read_metrics()
            except Exception:
                LOG.exception('Error occurred while reading metrics messages.')

    def stop(self):
        self._consume_kafka_conn.close()


class AlarmDefinitionConsumer(threading.Thread):
    """The thread to process alarm definitions.

    This class will get alarm definition messages from kafka,
    Then init new processor, update existing processor or delete processor
    according to the request.
    """
    def __init__(self, t_name, tp):
        threading.Thread.__init__(self, name=t_name)

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
        # get the dict where all processors are indexed
        self.threshold_processors = tp
        # get the time interval to query es
        self.interval = cfg.CONF.alarmdefinitions.check_alarm_def_interval
        # set the flag, which is used to determine if a processor is expired
        # each processor will has its flag, if same with self.flag, it's valid
        self.flag = 0
        # setup query params
        self.params = self._build_alarm_definitions_query(
            cfg.CONF.alarmdefinitions.name,
            cfg.CONF.alarmdefinitions.dimensions)

    def _build_alarm_definitions_query(self, name, dimensions):
        query = {}
        queries = []
        field_string = 'alarmdefinitions.expression_data.dimensions.'
        if dimensions:
            # add dimensions to query params
            current_dimension_split = (
                dimensions.split(','))
            for current_dimension in current_dimension_split:
                current_dimen_data = current_dimension.split(':')
                queries.append({'query_string': {
                    'default_field': (field_string +
                                      current_dimen_data[0]),
                    'query': current_dimen_data[1]}})
        if name:
            # add name to query params
            queries.append({'query_string': {
                'default_field': 'name', 'query': name}})
        # finally build the query
        query = {'query': {'bool': {'must': queries}}}
        return query

    def _get_alarm_definitions_response(self, res):
        if res and res.status_code == 200:
            obj = res.json()
            if obj:
                return obj.get('hits')
        return None

    def get_alarm_definitions(self):
        """Get alarm definitions from es."""
        es_res = self._es_conn.get_messages(self.params)
        es_res = self._get_alarm_definitions_response(es_res)
        if es_res is None:
            return None
        LOG.debug('Query to ElasticSearch returned: %s' % es_res)
        if es_res["hits"]:
            return es_res["hits"]
        else:
            return []

    def refresh_alarm_processors(self):
        def create_alarm_processor():
            # make sure received a new alarm definition
            if aid in self.threshold_processors:
                LOG.debug('already exsist alarm definition')
                return
            # init a processor for this alarm definition
            temp_processor = (
                driver.DriverManager(
                    namespace.PROCESSOR_NS,
                    cfg.CONF.thresholdengine.processor,
                    invoke_on_load=True,
                    invoke_args=(alarm_def,)).driver)
            # register this new processor
            self.threshold_processors[aid] = {}
            self.threshold_processors[aid]['processor'] = (
                temp_processor)
            self.threshold_processors[aid]['flag'] = self.flag
            self.threshold_processors[aid]['json'] = alarm_def

        def update_alarm_processor():
            # update the processor when alarm definition is changed
            updated = False
            if aid in self.threshold_processors:
                updated = (self.threshold_processors
                           [aid]['processor']
                           .update_thresh_processor(alarm_def))
                self.threshold_processors[aid]['json'] = alarm_def
            if updated:
                LOG.debug('alarm definition updates successfully!')
            else:
                LOG.debug('alarm definition update fail!')

        def delete_alarm_processor():
            # delete related processor when an alarm definition is deleted
            if aid in self.threshold_processors:
                self.threshold_processors.pop(aid)

        self.flag = 1 - self.flag
        # get all alarm definitions from es to update those in the engine
        alarm_definitions = self.get_alarm_definitions()
        # http request fails, do nothing
        if alarm_definitions is None:
            return
        if lock.acquire():
            for alarm_definition in alarm_definitions:
                alarm_def = alarm_definition['_source']
                aid = alarm_def['id']
                if aid in self.threshold_processors:
                    # alarm definition is updated
                    if alarm_def != self.threshold_processors[aid]['json']:
                        update_alarm_processor()
                    self.threshold_processors[aid]['flag'] = self.flag
                else:
                    # comes a new alarm definition
                    create_alarm_processor()
            for aid in self.threshold_processors.keys():
                if self.threshold_processors[aid]['flag'] != self.flag:
                    # the alarm definition is expired
                    delete_alarm_processor()
        lock.release()

    def run(self):
        while True:
            try:
                self.refresh_alarm_processors()
                time.sleep(self.interval)
            except Exception:
                LOG.exception('Error occurred '
                              'while reading alarm definitions.')

    def stop(self):
        pass


class ThresholdEngine(os_service.Service):
    def __init__(self, threads=1000):
        super(ThresholdEngine, self).__init__(threads)
        # dict to index all the processors,
        # key = alarm def id; value = processor
        self.threshold_processors = {}
        # init threads for processing metrics, alarm definition and alarm
        try:
            self.thread_alarm = AlarmPublisher(
                'alarm_publisher',
                self.threshold_processors)
        except Exception:
            self.thread_alarm = None
        try:
            self.thread_alarm_def = AlarmDefinitionConsumer(
                'alarm_def_consumer',
                self.threshold_processors)
        except Exception:
            self.thread_alarm_def = None
        try:
            self.thread_metrics = MetricsConsumer(
                'metrics_consumer',
                self.threshold_processors)
        except Exception:
            self.thread_metrics = None

    def start(self):
        try:
            self.thread_alarm.start()
            self.thread_alarm_def.start()
            self.thread_metrics.start()
            LOG.info('Starting thresh processing succeed!')
        except Exception:
            LOG.debug('Starting thresh processing failed!')

    def stop(self):
        try:
            if self.thread_alarm:
                self.thread_alarm.stop()
            if self.thread_alarm_def:
                self.thread_alarm_def.stop()
            if self.thread_metrics:
                self.thread_metrics.stop()
        except Exception:
            LOG.debug('Terminate thresh process threads error')
        super(ThresholdEngine, self).stop()
