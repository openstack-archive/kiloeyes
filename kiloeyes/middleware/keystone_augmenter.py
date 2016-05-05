# Copyright 2016 Cornell University
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


import StringIO
try:
    import ujson as json
except ImportError:
    import json


class KeystoneAugmenter(object):
    """middleware that adds keystone data to POST-ed metrics.

       This middleware must be placed in the server pipeline immediately
       following the keystone middleware. If the request coming to the server
       is a POST request on the /v2.0/metrics endpoint, the middleware extracts
       keystone fields from the request,and adds them to the body of the
       metrics JSON objects.
    """
    def __init__(self, app, conf):
        self.app = app
        self.conf = conf

    def add_keystone_to_metrics(self, env):
        body = env['wsgi.input'].read()
        metrics = json.loads(body)

        # Add keystone data to metrics
        if isinstance(metrics, list):
            for metric in metrics:
                metric['tenant'] = env['HTTP_X_TENANT']
                metric['tenant_id'] = env['HTTP_X_TENANT_ID']
                metric['user'] = env['HTTP_X_USER']
                metric['user_agent'] = env['HTTP_USER_AGENT']
                metric['project_id'] = env['HTTP_X_PROJECT_ID']
                metric['user_id'] = env['HTTP_X_USER_ID']

        env['wsgi.input'] = StringIO.StringIO(json.dumps(metrics))
        return env

    def __call__(self, env, start_response):
        if (env.get('PATH_INFO', '').startswith('/v2.0/metrics') and
                env.get('REQUEST_METHOD', '') == 'POST'):
            # We only check the requests which are posting against metrics
            # endpoint
            try:
                env = self.add_keystone_to_metrics(env)

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

    def augmenter_filter(app):
        return KeystoneAugmenter(app, local_conf)

    return augmenter_filter
