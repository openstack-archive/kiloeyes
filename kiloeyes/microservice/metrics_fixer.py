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


import hashlib
import json
import time

from oslo_log import log

LOG = log.getLogger(__name__)


class MetricsFixer(object):
    def __init__(self):
        LOG.debug('initializing MetricsFixer!')
        super(MetricsFixer, self).__init__()

    @staticmethod
    def _add_hash(message):
        # If there is no timestamp, we need to fix that up
        if not message.get('timestamp'):
            message['timestamp'] = time.time()

        # fixup the dimensions_hash
        if not message.get('dimensions_hash') and message.get('dimensions'):
            key_str = json.dumps(message['dimensions'],
                                 sort_keys=True, indent=None,
                                 separators=(',', ':'))
            message['dimensions_hash'] = hashlib.md5(key_str).hexdigest()

        return json.dumps(message, sort_keys=False, indent=None,
                          separators=(',', ':'))

    def process_msg(self, msg):
        try:
            data = json.loads(msg)
            #if not isinstance(data, list):
            #    data = [data]
            #result = ''
            #for item in data:
            #    result += '{"index":{}}\n' + MetricsFixer._add_hash(item)
            #    result += '\n'
            return MetricsFixer._add_hash(data)
        except Exception:
            LOG.exception('')
            return ''
