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

agg_ops = {'SUM': sum,
           'AVG': lambda x: sum(x) / len(x),
           'MAX': max,
           'MIN': min,
           'COUNT': len}


comp_ops = {'GT': lambda x, y: x <= y,
            'LT': lambda x, y: x >= y,
            'LTE': lambda x, y: x > y,
            'GTE': lambda x, y: x < y}

STATE_OK = 'OK'
STATE_ALARM = 'ALARM'
STATE_UNDETERMINED = 'UNDETERMINED'


def calc_value(func, data_list):
    """Calc float values according to 5 functions."""

    if (func not in agg_ops or
            (len(data_list) == 0 and func != 'COUNT')):
        return None
    else:
        return agg_ops[func](data_list)


def compare_thresh(values, op, thresh):
    """Check if value from metrics exceeds thresh.

    Only the value in each period meet thresh, the alarm state can be 'ALARM'.

    For example, the alarm definition defines 3 periods, values = [a,b,c].
    If the value in any period doesn't meet thresh,
    then alarm state must be 'OK';
    If some values are None (means no metrics in that period)
    but all other values meet thresh,
    we still don't know if the alarm can be triggered,
    so it's 'UNDETERMINED';
    otherwise, the state can be 'ALARM'
    """
    for value in values:
        if value is not None and comp_ops[op](value, thresh):
            return STATE_OK

    state = STATE_ALARM
    for value in values:
        if value is None:
            state = STATE_UNDETERMINED
    return state


def calc_logic(logic_operator, subs):
    """Calc overall state of an alarm expression.

    'OK' means False;
    'ALARM' means True;
    'UNDETERMINED' means either True or False.
    """
    if logic_operator == 'AND':
        state = 'ALARM'
        for o in subs:
            if o == 'OK':
                return 'OK'
            elif o == 'UNDETERMINED':
                state = 'UNDETERMINED'
        return state
    elif logic_operator == 'OR':
        state = 'OK'
        for o in subs:
            if o == 'ALARM':
                return 'ALARM'
            elif o == 'UNDETERMINED':
                state = 'UNDETERMINED'
        return state
    else:
        return 'UNDETERMINED'
