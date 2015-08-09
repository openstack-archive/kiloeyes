#!/usr/bin/env python
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
import oslo_i18n
from oslo_log import log
import sys

from kiloeyes.common import constant

LOG = log.getLogger(__name__)


def prepare_service(argv=None):
    oslo_i18n.enable_lazy()
    log.set_defaults(constant.KILOEYES_LOGGING_CONTEXT_FORMAT,
                     constant.KILOEYES_LOG_LEVELS)
    log.register_options(cfg.CONF)

    if argv is None:
        argv = sys.argv
    cfg.CONF(argv[1:], project='kiloeyes')
    log.setup(cfg.CONF, 'kiloeyes')
    LOG.info('Service has started!')
