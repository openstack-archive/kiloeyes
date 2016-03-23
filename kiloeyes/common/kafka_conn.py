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

import time

from kafka import client
from kafka import common
from kafka import consumer
from kafka import producer
from oslo_config import cfg
from oslo_config import types

try:
    import ujson as json
except ImportError:
    import json

from oslo_log import log


KAFKA_OPTS = [
    cfg.StrOpt('uri', help='Address to kafka server. For example: '
               'uri=192.168.1.191:9092'),
    cfg.StrOpt('group', default='api',
               help='The group name that this service belongs to.'),
    cfg.IntOpt('wait_time', default=1,
               help='The wait time when no messages on kafka queue.'),
    cfg.IntOpt('ack_time', default=20,
               help='The ack time back to kafka.'),
    cfg.IntOpt('max_retry', default=3,
               help='The number of retry when there is a connection error.'),
    cfg.BoolOpt('auto_commit', default=True,
                help='If automatically commmit when consume messages.'),
    cfg.BoolOpt('async', default=True, help='The type of posting.'),
    cfg.BoolOpt('compact', default=True,
                help=('Specify if the message received should be parsed. '
                      'If True, message will not be parsed, otherwise '
                      'messages will be parsed.')),
    cfg.ListOpt('partitions',
                default=['0'],
                help='The sleep time when no messages on kafka queue.'),
    cfg.BoolOpt('drop_data', default=False,
                help=('Specify if received data should be simply dropped. '
                      'This parameter is only for testing purposes.')),
]

cfg.CONF.register_opts(KAFKA_OPTS, group="kafka_opts")

LOG = log.getLogger(__name__)


class KafkaConnection(object):

    def __init__(self, topic):
        if not cfg.CONF.kafka_opts.uri:
            raise Exception('Kafka is not configured correctly! '
                            'Use configuration file to specify Kafka '
                            'uri, for example: '
                            'uri=192.168.1.191:9092')

        self.uri = cfg.CONF.kafka_opts.uri
        self.topic = topic
        self.group = cfg.CONF.kafka_opts.group
        self.wait_time = cfg.CONF.kafka_opts.wait_time
        self.async = cfg.CONF.kafka_opts.async
        self.ack_time = cfg.CONF.kafka_opts.ack_time
        self.max_retry = cfg.CONF.kafka_opts.max_retry
        self.auto_commit = cfg.CONF.kafka_opts.auto_commit
        self.compact = cfg.CONF.kafka_opts.compact
        self.partitions = [int(x) for x in cfg.CONF.kafka_opts.partitions]
        self.drop_data = cfg.CONF.kafka_opts.drop_data

        self._client = None
        self._consumer = None
        self._producer = None

        LOG.debug('Kafka Connection initialized successfully!')

    def _init_client(self, wait_time=None):
        for i in range(self.max_retry):
            try:
                # if there is a client instance, but _init_client is called
                # again, most likely the connection has gone stale, close that
                # connection and reconnect.
                if self._client:
                    self._client.close()

                if not wait_time:
                    wait_time = self.wait_time
                time.sleep(wait_time)

                self._client = client.KafkaClient(self.uri)

                # when a client is re-initialized, existing consumer should be
                # reset as well.
                self._consumer = None
                self._producer = None
                LOG.debug("Successfully connected to Kafka server at topic: "
                          "\"%s\" partitions %s" % (self.topic,
                                                    self.partitions))
                break
            except common.KafkaUnavailableError:
                LOG.error('Kafka server at %s is down.' % self.uri)
            except common.LeaderNotAvailableError:
                LOG.error('Kafka at %s has no leader available.' % self.uri)
            except Exception:
                LOG.error('Kafka at %s initialization failed.' % self.uri)
            # Wait a bit and try again to get a client
            time.sleep(self.wait_time)

    def _init_consumer(self):
        try:
            if not self._client:
                self._init_client()
            self._consumer = consumer.SimpleConsumer(
                self._client, self.group, self.topic,
                auto_commit=self.auto_commit,
                partitions=self.partitions)
            LOG.debug('Consumer was created successfully.')
        except Exception:
            self._consumer = None
            LOG.exception('Kafka (%s) consumer can not be created.' %
                          self.uri)

    def _init_producer(self):
        try:
            if not self._client:
                self._init_client()
            self._producer = producer.SimpleProducer(
                self._client, async=self.async, ack_timeout=self.ack_time)
            LOG.debug('Producer was created successfully.')
        except Exception:
            self._producer = None
            LOG.exception('Kafka (%s) producer can not be created.' %
                          self.uri)

    def commit(self):
        if self._consumer and self.auto_commit:
            self._consumer.commit()

    def close(self):
        if self._client:
            self._consumer = None
            self._producer = None
            self._client.close()

    def get_messages(self):
        try:
            if not self._consumer:
                self._init_consumer()

            for msg in self._consumer:
                if msg.message:
                    LOG.debug(msg.message.value)
                    yield msg
        except common.OffsetOutOfRangeError:
            self._consumer.seek(0, 0)
            LOG.error('Seems consumer has been down for a long time.')
            yield None
        except Exception as ex:
            LOG.exception(ex)
            self._consumer = None
            yield None

    def send_messages(self, messages):
        LOG.debug('Prepare to send messages.')
        if not messages or self.drop_data:
            return 204

        code = 400
        try:
            if not self._producer:
                self._init_producer()

            LOG.debug('Start sending messages to kafka.')
            if self.compact:
                self._producer.send_messages(self.topic, messages)
            else:
                data = json.loads(messages)
                LOG.debug('Msg parsed successfully.')
                if isinstance(data, list):
                    for item in data:
                        self._producer.send_messages(
                            self.topic, json.dumps(item))
                else:
                    self._producer.send_messages(self.topic, messages)
            LOG.debug('Message posted successfully.')
            code = 204
        except (common.KafkaUnavailableError,
                common.LeaderNotAvailableError):
            self._client = None
            code = 503
            LOG.exception('Error occurred while posting data to Kafka.')
        except ValueError:
            code = 406
            LOG.exception('Message %s is not valid json.' % messages)
        except Exception:
            code = 500
            LOG.exception('Unknown error.')

        return code
