#!/usr/bin/python
# Copyright 2014 IBM Corp
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

# this script will create a set of metrics at the endpoint specified as the
# program parameter
#
#

import json
import random
import requests
import string
import sys
import time


MOLD = {"name": "name1",
        "timestamp": '2014-12-01',
        "value": 100
        }

MOLD_DIMENSIONS = {"key1": None}


def setup_metrics(argv):

    for a in range(100):
        MOLD_DIMENSIONS['key1'] = (
            ''.join(random.sample(string.ascii_uppercase * 6, 6)))
        MOLD_DIMENSIONS['key2'] = (
            ''.join(random.sample(string.ascii_uppercase * 6, 6)))
        MOLD_DIMENSIONS['key_' + str(a)] = (
            ''.join(random.sample(string.ascii_uppercase * 6, 6)))

        """
        import hashlib
        key_str = json.dumps(MOLD_DIMENSIONS, sort_keys=True,
                             indent=None,
                             separators=(',', ':'))

        key = hashlib.md5(key_str).hexdigest()
        MOLD['dimensions_hash'] = key
        """

        MOLD['dimensions'] = MOLD_DIMENSIONS

        print('starting round %s' % a)
        # Generate unique 100 metrics
        for i in range(100):
            MOLD['name'] = ''.join(random.sample(string.ascii_uppercase * 6,
                                                 6))

            for j in range(10):
                MOLD['value'] = round((i + 1) * j * random.random(), 2)
                the_time = time.time()
                # single messages
                for k in range(10):
                    factor = round(random.random(), 2) * 100
                    MOLD['timestamp'] = the_time + k * 50000 * factor
                    MOLD['value'] = i * j * k * random.random()
                    res = requests.post(argv[1], data=json.dumps(MOLD))
                    if res.status_code != 201 and res.status_code != 204:
                        print(json.dumps(MOLD))
                        exit(0)
                # multiple messages
                for k in range(3):
                    msg = "["
                    factor = round(random.random(), 2) * 100
                    MOLD['timestamp'] = the_time + k * 50000 * factor
                    MOLD['value'] = i * j * k * random.random()
                    msg += json.dumps(MOLD)

                    for l in range(9):
                        factor = round(random.random(), 2) * 100
                        MOLD['timestamp'] = the_time + k * 50000 * factor
                        MOLD['value'] = i * j * k * random.random()
                        msg += ',' + json.dumps(MOLD)
                    msg += "]"
                    res = requests.post(argv[1], data=msg)
                    if res.status_code != 201 and res.status_code != 204:
                        print(json.dumps(MOLD))
                        exit(0)
        del MOLD_DIMENSIONS['key_' + str(a)]
        print('round finished %s' % a)

if __name__ == '__main__':
    if len(sys.argv) == 2:
        setup_metrics(sys.argv)
    else:
        print('Usage: setup_metrics endpoint. For example:')
        print('       setup_metrics http://host:9000/data_2015')
