#
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

from oslo_config import cfg
from oslo_log import log
from stevedore import driver

from kiloeyes.common import es_conn
from kiloeyes.common import kafka_conn
from kiloeyes.common import namespace
from kiloeyes.openstack.common import service as os_service

OPTS = [
    cfg.StrOpt('topic', default='metrics',
               help=('The topic that messages will be retrieved from.'
                     'This also will be used as a doc type when saved '
                     'to ElasticSearch.')),
    cfg.StrOpt('doc_type', default='',
               help=('The document type which defines what document '
                     'type the messages will be save into. If not '
                     'specified, then the topic will be used.')),
    cfg.StrOpt('index_strategy', default='fixed',
               help='The index strategy used to create index name.'),
    cfg.StrOpt('index_prefix', default='data_',
               help='The index prefix where metrics were saved to.'),
    cfg.StrOpt('processor', default='',
               help=('The message processer to load to process the message.'
                     'If the message does not need to be process anyway,'
                     'leave the default')),
]

cfg.CONF.register_opts(OPTS, group="es_persister")

LOG = log.getLogger(__name__)


class ESPersister(os_service.Service):

    def __init__(self, threads=1000):
        super(ESPersister, self).__init__(threads)
        self._kafka_conn = kafka_conn.KafkaConnection(
            cfg.CONF.es_persister.topic)

        # load index strategy
        if cfg.CONF.es_persister.index_strategy:
            self.index_strategy = driver.DriverManager(
                namespace.STRATEGY_NS,
                cfg.CONF.es_persister.index_strategy,
                invoke_on_load=True,
                invoke_kwds={}).driver
            LOG.debug(dir(self.index_strategy))
        else:
            self.index_strategy = None

        self.index_prefix = cfg.CONF.es_persister.index_prefix
        # Use doc_type if it is defined.
        if cfg.CONF.es_persister.doc_type:
            self.doc_type = cfg.CONF.es_persister.doc_type
        else:
            self.doc_type = cfg.CONF.es_persister.topic

        # create connection to ElasticSearch
        self._es_conn = es_conn.ESConnection(
            self.doc_type, self.index_strategy, self.index_prefix)

        # load message processor
        if cfg.CONF.es_persister.processor:
            self.msg_processor = driver.DriverManager(
                namespace.PROCESSOR_NS,
                cfg.CONF.es_persister.processor,
                invoke_on_load=True,
                invoke_kwds={}).driver
            LOG.debug(dir(self.msg_processor))
        else:
            self.msg_processor = None

    def start(self):
        while True:
            try:
                for msg in self._kafka_conn.get_messages():
                    if msg and msg.message:
                        LOG.debug(msg.message.value)
                        if self.msg_processor:
                            value = self.msg_processor.process_msg(
                                msg.message.value)
                        else:
                            value = msg.message.value
                        if value:
                            self._es_conn.send_messages(value)
                # if autocommit is set, this will be a no-op call.
                self._kafka_conn.commit()
            except Exception:
                LOG.exception('Error occurred while handling kafka messages.')

    def stop(self):
        self._kafka_conn.close()
        super(ESPersister, self).stop()
