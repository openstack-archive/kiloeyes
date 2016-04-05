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


class MeterValidator(object):
    """middleware that validate the meter input stream.

    This middleware checks if the input stream actually follows meter spec
    and all the messages in the request has valid meter data. If the body
    is valid json and compliant with the spec, then the request will forward
    the request to the next in the pipeline, otherwise, it will reject the
    request with response code of 400 or 406.
    """
    def __init__(self, app, conf):
        self.app = app
        self.conf = conf

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
            meter.get('message_id') and meter.get('project_id') and
            meter.get('source') and meter.get('timestamp') and
                meter.get('user_id')):
            return True
        else:
            return False

    def __call__(self, env, start_response):
        # if request starts with /datapoints/, then let it go on.
        # this login middle
        if (env.get('PATH_INFO', '').startswith('/v2.0/meters') and
                env.get('REQUEST_METHOD', '') == 'POST'):
            # We only check the requests which are posting against meters
            # endpoint
            try:
                body = env['wsgi.input'].read()
                meters = json.loads(body)
                # Do business logic validation here.
                is_valid = True
                if isinstance(meters, list):
                    for meter in meters:
                        if not self._is_valid_meter(meter):
                            is_valid = False
                            break
                else:
                    is_valid = self._is_valid_meter(meters)

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
                    msg = {'meter': meters,
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
        return MeterValidator(app, local_conf)

    return validator_filter
