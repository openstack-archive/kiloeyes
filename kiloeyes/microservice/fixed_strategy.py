#
# Copyright 2012-2013 eNovance <licensing@enovance.com>
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

from kiloeyes.openstack.common import log

LOG = log.getLogger(__name__)

OPTS = [
    cfg.StrOpt('index_name',
               default='',
               help='The pre-configured index name.'),
]

cfg.CONF.register_opts(OPTS, group="fixed_strategy")


class FixedStrategy(object):
    """This strategy returns an empty string."""

    def __init__(self):
        self.index_name = cfg.CONF.fixed_strategy.index_name
        LOG.debug('EmptyStrategy initialized successfully!')

    def get_index(self):
        return self.index_name
