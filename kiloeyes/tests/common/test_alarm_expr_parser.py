# -*- coding: utf-8 -*-
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

from kiloeyes.common import alarm_expr_parser
from kiloeyes.openstack.common import log
from kiloeyes import tests

LOG = log.getLogger(__name__)


class TestAlarmExprParser(tests.BaseTestCase):
    def __init__(self, *args, **kwargs):
        super(TestAlarmExprParser, self).__init__(*args, **kwargs)
        self.expr0 = (
            "max(-_.千幸福的笑脸{घोड़ा=馬,  "
            "dn2=dv2,千幸福的笑脸घ=千幸福的笑脸घ}) gte 100 "
            "times 3 And "
            "(min(ເຮືອນ{dn3=dv3,家=дом}) < 10 or sum(biz{dn5=dv58}) >9 9and "
            "count(fizzle) lt 0 or count(baz) > 1)".decode('utf8'))

        self.expr1 = ("max(foo{hostname=mini-mon,千=千}, 120)"
                      " > 100 and (max(bar)>100 "
                      " or max(biz)>100)".decode('utf8'))

        self.expr2 = "max(foo)>=100 times 10"

        self.expr3 = "max(foo)>=100 time 10"

        self.expr4 = ("max(foo{hostname=mini-mon,千==千}, 120)"
                      " > 100 and (max(bar)>100 "
                      " or max(biz)>100)".decode('utf8'))

        self.expr5 = "maxi(foo)>=100 times 10"

        self.expr6 = ("max(foo{hostname=mini-mon,千=千}, 120)"
                      " = 100 and (max(bar)>100 "
                      " or max(biz)>100)".decode('utf8'))

        self.expr7 = "(max(foo)>=100 times 10"

        self.expr8 = ("max(foo,me{hostname=mini-mon,千=千}, 120)"
                      " = 100 and (max(bar)>100 "
                      " or max(biz)>100)".decode('utf8'))

    def setUp(self):
        super(TestAlarmExprParser, self).setUp()

    def test_wrong_input(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr3).parse_result
        self.assertEqual(None, expr)
        expr = alarm_expr_parser.AlarmExprParser(self.expr4).parse_result
        self.assertEqual(None, expr)
        expr = alarm_expr_parser.AlarmExprParser(self.expr5).parse_result
        self.assertEqual(None, expr)
        expr = alarm_expr_parser.AlarmExprParser(self.expr6).parse_result
        self.assertEqual(None, expr)
        expr = alarm_expr_parser.AlarmExprParser(self.expr7).parse_result
        self.assertEqual(None, expr)

    def test_logic(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr0).parse_result
        self.assertEqual(u'AND', expr.logic_operator)
        self.assertEqual(None, expr.sub_expr_list[0].logic_operator)
        self.assertEqual(u'OR', expr.sub_expr_list[1].logic_operator)
        self.assertEqual(u'AND', expr.sub_expr_list[1].
                         sub_expr_list[1].logic_operator)

        expr = alarm_expr_parser.AlarmExprParser(self.expr1).parse_result
        self.assertEqual(u'AND', expr.logic_operator)
        self.assertEqual('OR', expr.sub_expr_list[1].logic_operator)
        self.assertEqual(None, expr.sub_expr_list[0].logic_operator)
        self.assertEqual(
            'max(foo{hostname=mini-mon,千=千}, 120) > 100'.decode('utf8'),
            expr.sub_expr_list[0].fmtd_sub_expr_str)

        expr = alarm_expr_parser.AlarmExprParser(self.expr2).parse_result
        self.assertEqual(None, expr.logic_operator)

    def test_expr(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr0).parse_result
        self.assertEqual("max(-_.千幸福的笑脸{घोड़ा=馬,"
                         "dn2=dv2,千幸福的笑脸घ=千幸福的笑脸घ})gte100"
                         "times3", expr.sub_expr_list[0].
                         sub_expr_str.encode('utf8'))
        self.assertEqual("sum(biz{dn5=dv58})>99",
                         expr.sub_expr_list[1].sub_expr_list[1].
                         sub_expr_list[0].sub_expr_str.encode('utf8'))

        expr = alarm_expr_parser.AlarmExprParser(self.expr2).parse_result
        self.assertEqual("max(foo)>=100times10",
                         expr.sub_expr_str.encode('utf8'))

    def test_func(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr1).parse_result
        self.assertEqual("max", expr.sub_expr_list[1].
                         sub_expr_list[1].func.encode('utf8'))

        expr = alarm_expr_parser.AlarmExprParser(self.expr2).parse_result
        self.assertEqual("max", expr.func.encode('utf8'))

    def test_threshold(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr1).parse_result
        self.assertEqual(100,
                         float(expr.sub_expr_list[1].
                               sub_expr_list[1].threshold.encode('utf8')))

        expr = alarm_expr_parser.AlarmExprParser(self.expr2).parse_result
        self.assertEqual(100, float(expr.threshold))

    def test_periods(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr1).parse_result
        self.assertEqual(1, int(expr.sub_expr_list[1].
                                sub_expr_list[1].periods.encode('utf8')))

        expr = alarm_expr_parser.AlarmExprParser(self.expr2).parse_result
        self.assertEqual(10, int(expr.periods))

    def test_period(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr1).parse_result
        self.assertEqual(60, int(expr.sub_expr_list[1].
                                 sub_expr_list[1].period.encode('utf8')))

    def test_operator(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr1).parse_result
        self.assertEqual('GT', expr.sub_expr_list[1].
                         sub_expr_list[1].normalized_operator.encode('utf8'))

        expr = alarm_expr_parser.AlarmExprParser(self.expr2).parse_result
        self.assertEqual('>=', expr.operator)

    def test_metric_name(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr1).parse_result
        self.assertEqual('biz', expr.sub_expr_list[1].
                         sub_expr_list[1].metric_name.encode('utf8'))

    def test_dimensions_str(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr2).parse_result
        temp = expr.dimensions_str
        self.assertEqual('', temp)

    def test_sub_expr_list(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr2).parse_result
        temp = expr.sub_expr_list
        self.assertEqual([], temp)

    def test_dimensions_list(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr0).parse_result
        temp = []
        for e in expr.sub_expr_list[0].dimensions_as_list:
            temp.append(e.encode('utf8'))
        self.assertEqual(['घोड़ा=馬', 'dn2=dv2',
                          '千幸福的笑脸घ=千幸福的笑脸घ'], temp)

        expr = alarm_expr_parser.AlarmExprParser(self.expr2).parse_result
        self.assertEqual([], expr.dimensions_as_list)

    def test_dimensions_dict(self):
        expr = alarm_expr_parser.AlarmExprParser(self.expr0).parse_result
        temp = {}
        od = expr.sub_expr_list[0].dimensions_as_dict
        for e in od.keys():
            temp[e.encode('utf8')] = od[e].encode('utf8')
        self.assertEqual({'घोड़ा': '馬',
                          'dn2': 'dv2',
                          '千幸福的笑脸घ': '千幸福的笑脸घ'}, temp)

        expr = alarm_expr_parser.AlarmExprParser(self.expr2).parse_result
        self.assertEqual({}, expr.dimensions_as_dict)

    def test_related_metrics(self):
        rm = alarm_expr_parser.AlarmExprParser(self.expr2).related_metrics
        e_result = []
        e_result.append({
            'name': 'foo',
            'dimensions': {}
        })
        self.assertEqual(e_result, rm)
        rm = alarm_expr_parser.AlarmExprParser(self.expr1).related_metrics
        self.assertEqual(3, len(rm))

    def test_sub_alarm_expressions(self):
        sae = (alarm_expr_parser.AlarmExprParser(self.expr1).
               sub_alarm_expressions)
        self.assertEqual(3, len(sae))

    def test_wrong_format_expr(self):
        sub_expr_list = (alarm_expr_parser.AlarmExprParser(self.expr8).
                         sub_expr_list)
        self.assertEqual(None, sub_expr_list)
