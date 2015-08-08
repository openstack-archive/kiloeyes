# Copyright 2015 Carnegie Mellon University
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

import collections
import copy
import json
from oslo_log import log
import uuid

from kiloeyes.common import alarm_expr_calculator as calculator
from kiloeyes.common import alarm_expr_parser as parser
from kiloeyes.openstack.common import timeutils as tu


LOG = log.getLogger(__name__)

reasons = {'ALARM': 'The alarm threshold(s) have '
                    'been exceeded for the sub-alarms',
           'OK': 'The alarm threshold(s) have '
                 'not been exceeded for the sub-alarms',
           'UNDETERMINED': 'Unable to determine the alarm state'}


class ThresholdProcessor(object):
    """Thresh processor.

    This processor is for alarm definitions with short period.
    It will store the metrics value/timestamp in memory using dict.

    The basic data structure is:
    ALL_DATA = {#match_by name#: ALARM_DATA}
    For example, an alarm def has "match_by": ["hostname", "os"]
    Metrics come in:
    Metrics_A -> 'dimensions': {'hostname': 'A', 'os': 'windows'}
    Metrics_B -> 'dimensions': {'hostname': 'B', 'os': 'unix'}
    Then, ALL_DATA = {'Awindows': ALARM_DATA, 'Bunix': ALARM_DATA}

    ALARM_DATA = {'state': #alarm state#,
    'timestamp': #timestamp#, data: SUB_ALARM_DATA, ...}
    It will hold the overall info of th alarm,
    like state, timestamps, and metrics data.

    SUB_ALARM_DATA = {#sub alarm expr#: METRICS}
    For example, alarm expr is 'max(cpu)>10 and avg(memory)<10'
    SUB_ALARM_DATA = {'max(cpu)>10': METRICS, 'avg(memory)<10': METRICS}

    METRICS = {'value': [X, ...], 'timestamp': [T, ...], 'sub_state': S}
    Other key/values in a metrics will not be stored here.
    The state here is the state of this sub_alarm.
    """
    def __init__(self, alarm_def):
        """One processor instance hold one alarm definition."""
        LOG.debug('initializing ThresholdProcessor!')
        super(ThresholdProcessor, self).__init__()
        self.alarm_definition = alarm_def
        self.expression = self.alarm_definition['expression']
        self.match_by = self.alarm_definition['match_by']
        self.expr_data_queue = {}
        self.related_metrics = {}
        if len(self.match_by) == 0:
            self.match_by = None
        alarm_parser = parser.AlarmExprParser(self.expression)
        self.parse_result = alarm_parser.parse_result
        self.sub_expr_list = alarm_parser.sub_expr_list
        self.related_metrics[None] = alarm_parser.related_metrics
        self.sub_alarm_expr = alarm_parser.sub_alarm_expressions
        LOG.debug('successfully initialize ThresholdProcessor!')

    def update_thresh_processor(self, alarm_def):
        """Update the processor with updated alarm definition."""
        def update_data():
            # inherit previous stored metrics values
            for name in self.expr_data_queue:
                ts = tu.utcnow_ts()
                new_expr_data_queue[name] = {
                    'data': {},
                    'state': 'UNDETERMINED',
                    'create_timestamp':
                        self.expr_data_queue[name]['create_timestamp'],
                    'update_timestamp': ts,
                    'state_update_timestamp':
                        self.expr_data_queue[name]['state_update_timestamp']
                }
                for i in range(0, len(new_sub_expr_list), 1):
                    expr_old = self.sub_expr_list[i].fmtd_sub_expr_str
                    expr_new = new_sub_expr_list[i].fmtd_sub_expr_str
                    new_expr_data_queue[name]['data'][expr_new] = {
                        'state': 'UNDETERMINED',
                        'metrics':
                            (self.expr_data_queue[name]
                             ['data'][expr_old]['metrics']),
                        'values': []}

        LOG.debug('update ThresholdProcessor!')
        new_alarm_definition = alarm_def
        new_expression = new_alarm_definition['expression']
        alarm_parser = parser.AlarmExprParser(new_expression)
        new_sub_expr_list = alarm_parser.sub_expr_list
        new_expr_data_queue = {}
        update_data()
        self.expr_data_queue = new_expr_data_queue
        self.sub_expr_list = new_sub_expr_list
        self.sub_alarm_expr = alarm_parser.sub_alarm_expressions
        self.parse_result = alarm_parser.parse_result
        self.alarm_definition = new_alarm_definition
        self.expression = new_expression
        self.match_by = self.alarm_definition['match_by']
        if '' in self.match_by:
            self.match_by.remove('')
        if len(self.match_by) == 0:
            self.match_by = None
        LOG.debug('successfully update ThresholdProcessor!')
        return True

    def process_metrics(self, metrics):
        """Add new metrics to matched expr."""
        try:
            data = json.loads(metrics)
            self.add_expr_metrics(data)
        except Exception:
            LOG.exception('Received a wrong format metrics')

    def process_alarms(self):
        """Called to produce alarms."""
        try:
            alarm_list = []
            for m in self.expr_data_queue.keys():
                is_updated = self.update_state(self.expr_data_queue[m])
                if is_updated:
                    alarm_list.append(self.build_alarm(m))
            return alarm_list
        except Exception:
            LOG.exception('process metrics error')
            return []

    def update_state(self, expr_data):
        """Update the state of each alarm under this alarm definition."""
        def _calc_state(operand):
            if operand.logic_operator:
                subs = []
                for o in operand.sub_expr_list:
                    subs.append(_calc_state(o))
                return calculator.calc_logic(operand.logic_operator, subs)
            else:
                return expr_data['data'][operand.fmtd_sub_expr_str]['state']

        for sub_expr in self.sub_expr_list:
            self.update_sub_expr_state(sub_expr, expr_data)
        state_new = _calc_state(self.parse_result)
        if state_new != expr_data['state']:
            expr_data['state_update_timestamp'] = tu.utcnow_ts()
            expr_data['update_timestamp'] = tu.utcnow_ts()
            expr_data['state'] = state_new
            return True
        else:
            return False

    def update_sub_expr_state(self, expr, expr_data):
        def _update_metrics():
            """Delete metrics not in period."""
            data_list = expr_data['data'][expr.fmtd_sub_expr_str]['metrics']
            start_time = t_now - (float(expr.period)) * int(expr.periods)
            while (len(data_list) != 0
                   and data_list[0]['timestamp'] < start_time):
                data_list.popleft()

        def _update_state():
            """Update state of a sub expr."""
            data_sub = expr_data['data'][expr.fmtd_sub_expr_str]
            data_list = data_sub['metrics']
            period = float(expr.period)
            periods = int(expr.periods)
            right = t_now
            left = right - period
            temp_data = []
            value_in_periods = []
            i = len(data_list) - 1
            while i >= 0:
                if data_list[i]['timestamp'] >= left:
                    temp_data.append(float(data_list[i]['value']))
                else:
                    value = calculator.calc_value(
                        expr.normalized_func, temp_data)
                    value_in_periods.append(value)
                    right = left
                    left = right - period
                    temp_data = []
                    i += 1
                i -= 1
            value = calculator.calc_value(
                expr.normalized_func, temp_data)
            value_in_periods.append(value)
            for i in range(len(value_in_periods), periods, 1):
                value_in_periods.append(
                    calculator.calc_value(expr.normalized_func, []))
            expr_data['data'][expr.fmtd_sub_expr_str]['values'] = (
                value_in_periods)
            expr_data['data'][expr.fmtd_sub_expr_str]['state'] = (
                calculator.compare_thresh(
                    value_in_periods,
                    expr.normalized_operator,
                    float(expr.threshold)))

        t_now = tu.utcnow_ts()
        _update_metrics()
        _update_state()

    def add_expr_metrics(self, data):
        """Add new metrics to matched place."""
        for sub_expr in self.sub_expr_list:
            self.add_sub_expr_metrics(sub_expr, data)

    def add_sub_expr_metrics(self, expr, data):
        """Add new metrics to sub expr place."""
        def _has_match_expr():
            if (data['name'].lower() != expr.normalized_metric_name):
                return False
            metrics_dimensions = {}
            if 'dimensions' in data:
                metrics_dimensions = data['dimensions']
            def_dimensions = expr.dimensions_as_dict
            for dimension_key in def_dimensions.keys():
                if dimension_key in metrics_dimensions:
                    if (metrics_dimensions[dimension_key].lower()
                            != def_dimensions[dimension_key].lower()):
                        return False
                else:
                    return False
            return True

        def _add_metrics():
            temp = None
            if self.match_by:
                q_name = self.get_matched_data_queue_name(data)
                if q_name:
                    temp = self.expr_data_queue[q_name]
            else:
                if None not in self.expr_data_queue:
                    self.create_data_item(None)
                temp = self.expr_data_queue[None]
            if temp:
                data_list = temp['data'][expr.fmtd_sub_expr_str]
                data_list['metrics'].append(
                    {'value': float(data['value']),
                     'timestamp': tu.utcnow_ts()})
                return True
            else:
                return False

        if _has_match_expr() and _add_metrics():
            LOG.debug("Alarm def: %s consumes the metrics!"
                      % self.alarm_definition['name'])
        else:
            LOG.debug("Alarm def: %s don't need the metrics!"
                      % self.alarm_definition['name'])

    def create_data_item(self, name):
        """If new match_up tuple, create new entry to store metrics value."""
        ts = tu.utcnow_ts()
        self.expr_data_queue[name] = {
            'data': {},
            'state': 'UNDETERMINED',
            'create_timestamp': ts,
            'update_timestamp': ts,
            'state_update_timestamp': ts}
        for expr in self.sub_expr_list:
            self.expr_data_queue[name]['data'][expr.fmtd_sub_expr_str] = {
                'state': 'UNDETERMINED',
                'metrics': collections.deque(),
                'values': []}

    def get_matched_data_queue_name(self, data):
        """Use dimensions in match_up to generate a name."""
        name = ''
        for m in self.match_by:
            if m in data['dimensions']:
                name = name + data['dimensions'][m] + ','
            else:
                return None
        if name in self.expr_data_queue:
            return name
        else:
            self.related_metrics[name] = []
            for m in self.related_metrics[None]:
                temp = copy.deepcopy(m)
                for match in self.match_by:
                    temp['dimensions'][match] = data['dimensions'][match]
                self.related_metrics[name].append(temp)
            self.create_data_item(name)
            return name

    def build_alarm(self, name):
        """Build alarm json."""
        alarm = {}
        id = str(uuid.uuid4())
        alarm['id'] = id
        alarm['alarm_definition'] = self.alarm_definition
        alarm['metrics'] = self.related_metrics[name]
        alarm['state'] = self.expr_data_queue[name]['state']
        alarm['reason'] = reasons[alarm['state']]
        alarm['reason_data'] = {}
        sub_alarms = []
        dt = self.expr_data_queue[name]['data']
        for expr in self.sub_expr_list:
            sub_alarms.append({
                'sub_alarm_expression':
                    self.sub_alarm_expr[expr.fmtd_sub_expr_str],
                'sub_alarm_state': dt[expr.fmtd_sub_expr_str]['state'],
                'current_values': dt[expr.fmtd_sub_expr_str]['values']
            })
        alarm['sub_alarms'] = sub_alarms
        ct = self.expr_data_queue[name]['create_timestamp']
        st = self.expr_data_queue[name]['state_update_timestamp']
        t = self.expr_data_queue[name]['update_timestamp']
        alarm['state_updated_timestamp'] = tu.iso8601_from_timestamp(st)
        alarm['updated_timestamp'] = tu.iso8601_from_timestamp(t)
        alarm['created_timestamp'] = tu.iso8601_from_timestamp(ct)
        return json.dumps(alarm)
