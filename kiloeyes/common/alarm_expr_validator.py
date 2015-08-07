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


import json
from kiloeyes.common import alarm_expr_parser as parser


key_set = ['expression',
           'alarm_actions',
           'ok_actions',
           'undetermined_actions',
           'match_by',
           'name',
           'description']


def is_valid_alarm_definition(alarm_def_json):
    alarm_definition = json.loads(alarm_def_json)
    for key in key_set:
        if key not in alarm_definition:
            return False
    expression = alarm_definition['expression']
    alarm_parser = parser.AlarmExprParser(expression)
    if not alarm_parser.parse_result:
        return False
    return True


def is_valid_update_alarm_definition(ori_alarm_def_json, new_alarm_def_json):
    # both should be valid alarm definition
    if (not (is_valid_alarm_definition(ori_alarm_def_json)
             and is_valid_alarm_definition(new_alarm_def_json))):
        return False
    ori_alarm_definition = json.loads(ori_alarm_def_json)
    new_alarm_definition = json.loads(new_alarm_def_json)

    # match_by should not change
    if ori_alarm_definition['match_by'] != new_alarm_definition['match_by']:
        return False

    ori_expression = ori_alarm_definition['expression']
    ori_alarm_parser = parser.AlarmExprParser(ori_expression)
    ori_sub_expr_list = ori_alarm_parser.sub_expr_list
    new_expression = new_alarm_definition['expression']
    new_alarm_parser = parser.AlarmExprParser(new_expression)
    new_sub_expr_list = new_alarm_parser.sub_expr_list

    # should have same number of sub alarm exprs
    l = len(ori_sub_expr_list)
    if not new_sub_expr_list or l != len(new_sub_expr_list):
        return False

    for i in range(l):
        sub_expr_ori = ori_sub_expr_list[i]
        sub_expr_new = new_sub_expr_list[i]
        # each metrics in alarm expr should remain the same
        if (sub_expr_ori.normalized_metric_name
                != sub_expr_new.normalized_metric_name):
            return False
        if (sub_expr_ori.dimensions_as_dict
                != sub_expr_new.dimensions_as_dict):
            return False

    return True
