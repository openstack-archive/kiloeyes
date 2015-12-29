# -*- coding: utf-8 -*-
# Copyright 2014 Hewlett-Packard
# Copyright 2015 Carnegie Mellon University
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
import itertools
import pyparsing


class SubExpr(object):
    def __init__(self, tokens):

        self._sub_expr = tokens
        self._func = tokens.func
        self._metric_name = tokens.metric_name
        self._dimensions = tokens.dimensions.dimensions_list
        self._operator = tokens.relational_op
        self._threshold = tokens.threshold
        self._period = tokens.period
        self._periods = tokens.periods
        self._id = None

    @property
    def sub_expr_str(self):
        """Get the entire sub expression as a string with no spaces."""
        return "".join(list(itertools.chain(*self._sub_expr)))

    @property
    def fmtd_sub_expr_str(self):
        """Get the entire sub expressions as a string with spaces."""
        result = "{}({}".format(self._func.encode('utf8'),
                                self._metric_name.encode('utf8'))

        if self._dimensions:
            result += "{{{}}}".format(self._dimensions.encode('utf8'))

        if self._period:
            result += ", {}".format(self._period.encode('utf8'))

        result += ")"

        result += " {} {}".format(self._operator.encode('utf8'),
                                  self._threshold.encode('utf8'))

        if self._periods:
            result += " times {}".format(self._periods.encode('utf8'))

        return result.decode('utf8')

    @property
    def dimensions_str(self):
        """Get all the dimensions as a single comma delimited string."""
        return self._dimensions

    @property
    def operands_list(self):
        """Get this sub expression as a list."""
        return [self]

    @property
    def logic_operator(self):
        return None

    @property
    def sub_expr_list(self):
        return []

    @property
    def func(self):
        """Get the function as it appears in the orig expression."""
        return self._func

    @property
    def normalized_func(self):
        """Get the function upper-cased."""
        return self._func.upper()

    @property
    def metric_name(self):
        """Get the metric name as it appears in the orig expression."""
        return self._metric_name

    @property
    def normalized_metric_name(self):
        """Get the metric name lower-cased."""
        return self._metric_name.lower()

    @property
    def dimensions_as_list(self):
        """Get the dimensions as a list."""
        if self._dimensions:
            return self._dimensions.split(",")
        else:
            return []

    @property
    def dimensions_as_dict(self):
        """Get the dimensions as a dict."""
        dimension_dict = {}
        for di in self.dimensions_as_list:
            temp = di.split("=")
            dimension_dict[temp[0]] = temp[1]
        return dimension_dict

    @property
    def operator(self):
        """Get the operator."""
        return self._operator

    @property
    def threshold(self):
        """Get the threshold value."""
        return self._threshold

    @property
    def period(self):
        """Get the period. Default is 60 seconds."""
        if self._period:
            return self._period
        else:
            return u'60'

    @property
    def periods(self):
        """Get the periods. Default is 1."""
        if self._periods:
            return self._periods
        else:
            return u'1'

    @property
    def normalized_operator(self):
        """Get the operator as one of LT, GT, LTE, or GTE."""
        if self._operator.lower() == "lt" or self._operator == "<":
            return u"LT"
        elif self._operator.lower() == "gt" or self._operator == ">":
            return u"GT"
        elif self._operator.lower() == "lte" or self._operator == "<=":
            return u"LTE"
        elif self._operator.lower() == "gte" or self._operator == ">=":
            return u"GTE"

    @property
    def id(self):
        """Get the id used to identify this sub expression in the repo."""
        return self._id

    @id.setter
    def id(self, id):
        """Set the d used to identify this sub expression in the repo."""
        self._id = id


class BinaryOp(object):
    def __init__(self, tokens):
        self.op = tokens[0][1]
        self.operands = tokens[0][0::2]
        if self.op == u'&&' or self.op == u'and':
            self.op = u'AND'
        if self.op == u'||' or self.op == u'or':
            self.op = u'OR'

    @property
    def operands_list(self):
        return ([sub_operand for operand in self.operands for sub_operand in
                 operand.operands_list])

    @property
    def logic_operator(self):
        return self.op

    @property
    def sub_expr_list(self):
        if self.op:
            return self.operands
        else:
            return []


class AndSubExpr(BinaryOp):
    """Expand later as needed."""
    pass


class OrSubExpr(BinaryOp):
    """Expand later as needed."""
    pass


COMMA = pyparsing.Literal(",")
LPAREN = pyparsing.Literal("(")
RPAREN = pyparsing.Literal(")")
EQUAL = pyparsing.Literal("=")
LBRACE = pyparsing.Literal("{")
RBRACE = pyparsing.Literal("}")

# Initialize non-ascii unicode code points in the Basic Multilingual Plane.
unicode_printables = u''.join(
    unichr(c) for c in xrange(128, 65536) if not unichr(c).isspace())

# Does not like comma. No Literals from above allowed.
valid_identifier_chars = (
    (unicode_printables + pyparsing.alphanums + ".-_#!$%&'*+/:;?@[\\]^`|~"))

metric_name = (
    pyparsing.Word(valid_identifier_chars, min=1, max=255)("metric_name"))
dimension_name = pyparsing.Word(valid_identifier_chars, min=1, max=255)
dimension_value = pyparsing.Word(valid_identifier_chars, min=1, max=255)

integer_number = pyparsing.Word(pyparsing.nums)
decimal_number = pyparsing.Word(pyparsing.nums + ".")

max = pyparsing.CaselessLiteral("max")
min = pyparsing.CaselessLiteral("min")
avg = pyparsing.CaselessLiteral("avg")
count = pyparsing.CaselessLiteral("count")
sum = pyparsing.CaselessLiteral("sum")
func = (max | min | avg | count | sum)("func")

less_than_op = (
    (pyparsing.CaselessLiteral("<") | pyparsing.CaselessLiteral("lt")))
less_than_eq_op = (
    (pyparsing.CaselessLiteral("<=") | pyparsing.CaselessLiteral("lte")))
greater_than_op = (
    (pyparsing.CaselessLiteral(">") | pyparsing.CaselessLiteral("gt")))
greater_than_eq_op = (
    (pyparsing.CaselessLiteral(">=") | pyparsing.CaselessLiteral("gte")))

# Order is important. Put longer prefix first.
relational_op = (
    less_than_eq_op | less_than_op | greater_than_eq_op | greater_than_op)(
    "relational_op")

AND = pyparsing.CaselessLiteral("and") | pyparsing.CaselessLiteral("&&")
OR = pyparsing.CaselessLiteral("or") | pyparsing.CaselessLiteral("||")
logical_op = (AND | OR)("logical_op")

times = pyparsing.CaselessLiteral("times")

dimension = pyparsing.Group(dimension_name + EQUAL + dimension_value)

# Cannot have any whitespace after the comma delimiter.
dimension_list = pyparsing.Group(pyparsing.Optional(
    LBRACE + pyparsing.delimitedList(dimension, delim=',', combine=True)(
        "dimensions_list") + RBRACE))

metric = metric_name + dimension_list("dimensions")
period = integer_number("period")
threshold = decimal_number("threshold")
periods = integer_number("periods")

expression = pyparsing.Forward()

sub_expression = (func + LPAREN + metric + pyparsing.Optional(
    COMMA + period) + RPAREN + relational_op + threshold + pyparsing.Optional(
    times + periods) | LPAREN + expression + RPAREN)

sub_expression.setParseAction(SubExpr)

expression = (
    pyparsing.operatorPrecedence(sub_expression,
                                 [(AND, 2, pyparsing.opAssoc.LEFT, AndSubExpr),
                                  (OR, 2, pyparsing.opAssoc.LEFT, OrSubExpr)]))


class AlarmExprParser(object):
    def __init__(self, expr):
        self._expr = expr
        self._expr.encode('utf8').replace(' ', '')
        try:
            self.parseResult = (expression + pyparsing.stringEnd).parseString(
                self._expr.replace(' ', ''))[0]
        except Exception:
            self.parseResult = None

    @property
    def parse_result(self):
        return self.parseResult

    @property
    def sub_expr_list(self):
        if self.parseResult:
            return self.parseResult.operands_list
        else:
            return None

    @property
    def related_metrics(self):
        """Get a list of all the metrics related with this expression."""
        related_metrics = []
        for expr in self.sub_expr_list:
            related_metrics.append({
                'name': expr.metric_name,
                'dimensions': expr.dimensions_as_dict
            })
        return related_metrics

    @property
    def sub_alarm_expressions(self):
        """Get a list of all the sub expr parsed information."""
        sub_alarm_expr = {}
        for expr in self.sub_expr_list:
            sub_alarm_expr[expr.fmtd_sub_expr_str] = {
                'function': expr.normalized_func,
                'metric_name': expr.normalized_metric_name,
                'dimensions': expr.dimensions_as_dict,
                'operator': expr.normalized_operator,
                'threshold': expr.threshold,
                'period': expr.period,
                'periods': expr.periods
            }
        return sub_alarm_expr
