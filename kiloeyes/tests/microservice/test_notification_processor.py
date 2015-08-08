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
import json
import mock
from oslo_log import log

from kiloeyes.common import email_sender
from kiloeyes.microservice import notification_processor
from kiloeyes import tests

LOG = log.getLogger(__name__)

response_str = """
    {
        "hits":{
            "hits":[
                {
                    "_score":1.0,
                    "_type":"notification_methods",
                    "_id":"c60ec47e-5038-4bf1-9f95-4046c6e9a719",
                    "_source":{
                        "type":"EMAIL",
                        "id":"c60ec47e-5038-4bf1-9f95-4046c6e9a719",
                        "name":"NotificationMethod",
                        "address":"hanc@andrew.cmu.edu"
                    },
                    "_index":"admin"
                }
            ],
            "total":1,
            "max_score":1.0
        },
        "_shards":{
            "successful":5,
            "failed":0,
            "total":5
        },
        "took":2
    }
"""


class Msg(object):
    class message(object):
        value = 'message content'


class Es_conn(object):
    def get_message_by_id(self, id):
        return response_str


class TestNotificationProcessor(tests.BaseTestCase):

    def setUp(self):
        super(TestNotificationProcessor, self).setUp()

    def test_handle_alarm_msg(self):
        _es_conn = Es_conn()
        msg = Msg()

        email_sender.EmailSender = mock.Mock()

        r = ("{'metrics': {'timestamp': 1432672915.409,"
             "'name': 'biz', 'value': 1500,"
             "'dimensions': {'key2': 'value2', 'key1': 'value1'}},"
             "'state_updated_timestamp': 1432672915,"
             "'state': 'ALARM',"
             "'alarm_definition':"
             "{'alarm_actions': ['c60ec47e-5038-4bf1-9f95-4046c6e9a759'],"
             "'undetermined_actions': "
             "['c60ec47e-5038-4bf1-9f95-4046c6e9a759'],"
             "'name': 'Average CPU percent greater than 10',"
             "'match_by': ['hostname'],"
             "'severity': 'LOW',"
             "'ok_actions': ['c60ec47e-5038-4bf1-9f95-4046c6e9a759'],"
             "'expression': 'max(foo{hostname=mini-mon,mu=na}, 120)"
             "> 1100 and max(bar { asd = asd} )>1200 or avg(biz)>1300',"
             "'id': 'c60ec47e-5038-4bf1-9f95-4046c6e91111',"
             "'description': 'The average CPU percent is greater than 10'}}")

        with mock.patch.object(email_sender.EmailSender, 'send_emails',
                               return_value=""):
            with mock.patch.object(notification_processor.
                                   NotificationProcessor,
                                   "_get_notification_method_response",
                                   return_value=json.loads(response_str).
                                   get("hits")):
                with mock.patch.object(json, 'loads',
                                       return_value=ast.literal_eval(r)):
                    np = notification_processor.NotificationProcessor()
                    np.handle_alarm_msg(_es_conn, msg)

                    self.assertEqual(np.email_addresses[0],
                                     "hanc@andrew.cmu.edu")
