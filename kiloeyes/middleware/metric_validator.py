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
import StringIO
try:
    import ujson as json
except ImportError:
    import json

class MetricValidator(object):
    """middleware that validate the metric or meter input stream.

    This middleware checks if the input stream actually follows metric or meter spec
    and all the messages in the request has valid metric data. If the body
    is valid json and compliant with the spec, then the request will forward
    the request to the next in the pipeline, otherwise, it will reject the
    request with response code of 400 or 406.
    """
    def __init__(self, app, conf):
        self.app = app
        self.conf = conf

    def _is_valid_metric(self, metric):
        """Validate a message

        The external message format is
        {
           "name":"name1",
           "dimensions":{
              "key1":"value1",
              "key2":"value2"
           },
           "timestamp":1405630174,
           "value":1.0
        }

        Once this is validated, the message needs to be transformed into
        the following internal format:

        The current valid message format is as follows (interna):
        {
            "metric": {"something": "The metric as a JSON object"},
            "meta": {
                "tenantId": "the tenant ID acquired",
                "region": "the region that the metric was submitted under",
            },
            "creation_time": "the time when the API received the metric",
        }
        """
        if (metric.get('name') and metric.get('dimensions') and
                metric.get('timestamp') and metric.get('value')):
            return True
        else:
            return False

    def _is_valid_meter(self, meter):
        """Validate a message

        According to the Ceilometer OldSample, the external message format is
        {
            "counter_name": "instance",
            "counter_type": "gauge",
            "counter_unit": "instance",
            "counter_volume": 1.0,
            "message_id": "5460acce-4fd6-480d-ab18-9735ec7b1996",
            "project_id": "35b17138-b364-4e6a-a131-8f3099c5be68",
            "recorded_at": "2016-04-21T00:07:20.174109",
            "resource_id": "bd9431c1-8d69-4ad3-803a-8d4a6b89fd36",
            "resource_metadata": {
                "name1": "value1",
                "name2": "value2"
            },
            "source": "openstack",
            "timestamp": "2016-04-21T00:07:20.174114",
            "user_id": "efd87807-12d2-4b38-9c70-5f5c2ac427ff"
        }

        Once this is validated, the message needs to be transformed into
        the following internal format:

        The current valid message format is as follows (interna):
        {
            "meter": {"something": "The meter as a JSON object"},
            "meta": {
                "tenantId": "the tenant ID acquired",
                "region": "the region that the metric was submitted under",
            },
            "creation_time": "the time when the API received the metric",
        }
        """
        if (meter.get('counter_name') and meter.get('counter_volume') and
            meter.get('timestamp')):
            return True
        else:
            return False

    def __call__(self, env, start_response):
        # if request starts with /datapoints/, then let it go on.
        # this login middle
        if ((env.get('PATH_INFO', '').startswith('/v2.0/metrics') and
                env.get('REQUEST_METHOD', '') == 'POST') or
           (env.get('PATH_INFO', '').startswith('/v2.0/meters') and
                env.get('REQUEST_METHOD', '') == 'POST')):
            # We only check the requests which are posting against metrics
            # or meters endpoint
            try:
                is_metric = env.get('PATH_INFO', '').startswith('/v2.0/metrics')
                body = env['wsgi.input'].read()
                _inputs = json.loads(body)
                # Do business logic validation here.
                is_valid = True
                if isinstance(_inputs, list):
                    for _input in _inputs:
                        if(is_metric):
                            if not self._is_valid_metric(_input):
                                is_valid = False
                                break
                        else:
                            if not self._is_valid_meter(_input):
                                is_valid = False
                                break
                else:
                    if(is_metric):
                        is_valid = self._is_valid_metric(_input)
                    else:
                        is_valid = self._is_valid_meter(_input)
                if is_valid:
                    # If the message is valid, then wrap it into this internal
                    # format. The tenantId should be available from the
                    # request since this should have been authenticated.
                    # ideally this transformation should be done somewhere
                    # else. For the sake of simplicity, do the simple one
                    # here to make the life a bit easier.

                    # TODO(HP) Add logic to get region id from request header
                    # HTTP_X_SERVICE_CATALOG, then find endpoints, then region
                    region_id = None
                    if(is_metric):
                        msg = {'metric': metrics,
                               'meta': {'tenantId': env.get('HTTP_X_PROJECT_ID'),
                                        'region': region_id},
                               'creation_time': datetime.datetime.now()}
                    else:
                        msg = {'meter': metrics,
                               'meta': {'tenantId': env.get('HTTP_X_PROJECT_ID'),
                                        'region': region_id},
                               'creation_time': datetime.datetime.now()}
                    env['wsgi.input'] = StringIO.StringIO(json.dumps(msg))
                    return self.app(env, start_response)
            except Exception:
                pass
            # It is either invalid or exceptioned out while parsing json
            # we will send the request back with 400.
            start_response("400 Bad Request", [], '')
            return []
        else:
            # not a metric post request, move on.
            return self.app(env, start_response)


def filter_factory(global_conf, **local_conf):

    def validator_filter(app):
        return MetricValidator(app, local_conf)

    return validator_filter
