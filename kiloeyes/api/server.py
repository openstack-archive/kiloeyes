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

import os
from oslo_config import cfg
from oslo_log import log
import paste.deploy
from stevedore import named
from wsgiref import simple_server

from kiloeyes.common import constant
from kiloeyes.common import namespace
from kiloeyes.common import resource_api

OPTS = [
    cfg.MultiStrOpt('dispatcher',
                    default=[],
                    help='Dispatchers to process data.'),
]
cfg.CONF.register_opts(OPTS)

LOG = log.getLogger(__name__)


def api_app(conf):
    log.set_defaults(constant.KILOEYES_LOGGING_CONTEXT_FORMAT,
                     constant.KILOEYES_LOG_LEVELS)
    log.register_options(cfg.CONF)

    if conf.get('name'):
        name = conf.get('name')
    else:
        name = 'kiloeyes'

    cfg.CONF(args=[], project=name)

    log.setup(cfg.CONF, name)

    LOG.debug("@API CONF: %s" % cfg.CONF.dispatcher)
    dispatcher_manager = named.NamedExtensionManager(
        namespace=namespace.DISPATCHER_NS,
        names=cfg.CONF.dispatcher,
        invoke_on_load=True,
        invoke_args=[cfg.CONF])

    if not list(dispatcher_manager):
        LOG.error('Failed to load any dispatchers for %s' %
                  namespace.DISPATCHER_NS)
        return None

    # Create the application
    app = resource_api.ResourceAPI()

    # add each dispatcher to the application to serve requests offered by
    # each dispatcher
    for driver in dispatcher_manager:
        LOG.debug("@API Dispatcher: %s" % driver.obj)
        app.add_route(None, driver.obj)

    LOG.debug('Dispatcher drivers have been added to the routes!')
    return app


if __name__ == '__main__':
    wsgi_app = (
        paste.deploy.loadapp('config:etc/kiloeyes.ini',
                             relative_to=os.getcwd()))
    httpd = simple_server.make_server('127.0.0.1', 9000, wsgi_app)
    httpd.serve_forever()
