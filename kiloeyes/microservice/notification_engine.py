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

from oslo_config import cfg
from oslo_log import log
from oslo_service import service as os_service
from stevedore import driver

from kiloeyes.common import es_conn
from kiloeyes.common import kafka_conn
from kiloeyes.common import namespace

NOTIFICATION_ENGINE_OPTS = [
    cfg.StrOpt('topic',
               default='alarms',
               help='The topic that messages will be retrieved from.'),
    cfg.StrOpt('doc_type',
               default='notificationmethods',
               help=('The document type which notification methods were '
                     'saved into.')),
    cfg.StrOpt('index_strategy', default='fixed',
               help='The index strategy used to create index name.'),
    cfg.StrOpt('index_prefix', default='',
               help='The index prefix where metrics were saved to.'),
    cfg.StrOpt('processor',
               default='',
               help=('The message processer to load to process the message.'
                     'If the message does not need to be process anyway,'
                     'leave the default')),
]

cfg.CONF.register_opts(NOTIFICATION_ENGINE_OPTS, group="notificationengine")

LOG = log.getLogger(__name__)


class NotificationEngine(os_service.Service):

    def __init__(self, threads=1000):
        super(NotificationEngine, self).__init__(threads)
        self._kafka_conn = kafka_conn.KafkaConnection(
            cfg.CONF.notificationengine.topic)
        self.doc_type = cfg.CONF.notificationengine.doc_type

        # load index strategy
        if cfg.CONF.notificationengine.index_strategy:
            self.index_strategy = driver.DriverManager(
                namespace.STRATEGY_NS,
                cfg.CONF.notificationengine.index_strategy,
                invoke_on_load=True,
                invoke_kwds={}).driver
            LOG.debug(dir(self.index_strategy))
        else:
            self.index_strategy = None

        self.index_prefix = cfg.CONF.notificationengine.index_prefix

        self._es_conn = es_conn.ESConnection(
            self.doc_type, self.index_strategy, self.index_prefix)

        if cfg.CONF.notificationengine.processor:
            self.notification_processor = driver.DriverManager(
                namespace.PROCESSOR_NS,
                cfg.CONF.notificationengine.processor,
                invoke_on_load=True,
                invoke_kwds={}).driver
            LOG.debug(dir(self.notification_processor))
        else:
            self.notification_processor = None

    def start(self):
        while True:
            try:
                for msg in self._kafka_conn.get_messages():
                    (self.notification_processor.
                        handle_alarm_msg(self._es_conn, msg))

                # if autocommit is set, this will be a no-op call.
                self._kafka_conn.commit()
            except Exception:
                LOG.exception('Error occurred while handling kafka messages.')

    def stop(self):
        self._kafka_conn.close()
        super(NotificationEngine, self).stop()
