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

import datetime
import dateutil.parser as dparser
from oslo_config import cfg
import time

from oslo_log import log


"""
The following strategy is to define how the a given date can be break up into
ranges which will be used to create new Elastic Search indices. For example:
    [strategy]
    pattern=m
    frequency=2
    start_date=2014-01-01

The above strategy will create a index every 2 months starting Jan 1, 2014
    [strategy]
    pattern=d
    frequency=5
    start_date=2014-01-01

The above strategy will create a index every 5 days starting Jan 1, 2014
"""
OPTS = [
    cfg.StrOpt('time_unit',
               default='m',
               help=('The time unit to create a index for a given date. '
                     'The valid values are h, d, w, m, y. Each means hour, '
                     'day, week, month and year respectively.')),
    cfg.IntOpt('frequency',
               default=1,
               help='The frequency of the pattern to make a date range.'),
    cfg.StrOpt('start_date',
               default='2014-01-01',
               help='The start date.'),
]

cfg.CONF.register_opts(OPTS, group="timed_strategy")

LOG = log.getLogger(__name__)


class TimedStrategy(object):

    def __init__(self):
        self.time_unit = cfg.CONF.timed_strategy.time_unit
        self.frequency = cfg.CONF.timed_strategy.frequency
        self.start_date = dparser.parse(cfg.CONF.timed_strategy.start_date,
                                        fuzzy=True)
        self.now = None
        LOG.debug('TimedStrategy initialized successfully!')

    def set_time(self, a_date):
        self.now = a_date

    def get_index(self):
        # Right now, only support frequency of 1.
        # To support any frequency greater than 1, we need more work.
        if self.now:
            a_date = self.now
        else:
            a_date = datetime.datetime.now()
        if isinstance(a_date, long) or isinstance(a_date, int):
            try:
                a_date = datetime.datetime.fromtimestamp(a_date)
            except Exception:
                return
        elif isinstance(a_date, datetime.datetime):
            pass
        else:
            try:
                a_date = dparser.parse(a_date, fuzzy=True)
            except Exception:
                return

        if self.time_unit is 'y':
            return "%04i0101000000" % a_date.year
        if self.time_unit is 'm':
            return "%04i%02i01000000" % (a_date.year, a_date.month)
        if self.time_unit is 'd':
            return "%04i%02i%02i000000" % (a_date.year, a_date.month,
                                           a_date.day)
        if self.time_unit is 'h':
            return "%04i%02i%02i%02i0000" % (a_date.year, a_date.month,
                                             a_date.day, a_date.hour)
        if self.time_unit is 'w':
            year, week, day = a_date.isocalendar()
            if day == 7:
                day_str = "%04i %i 0" % (year, week)
            else:
                day_str = "%04i %i 0" % (year, week - 1)
            day = time.strptime(day_str, '%Y %U %w')
            return "%04i%02i%02i000000" % (day.tm_year, day.tm_mon,
                                           day.tm_mday)
