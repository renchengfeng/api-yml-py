"""测试专用算子：导入即注册（category=test）。"""
from __future__ import annotations

import time

from lowcode import Field, Operator, register


@register("sleep", category="test")
class Sleep(Operator):
    """睡眠后返回 value（测并行与超时）。"""

    spec = {"seconds": Field((int, float), default=0.1), "value": Field(object, dynamic=True)}

    def execute(self, ctx, args):
        time.sleep(args["seconds"])
        return args["value"]


@register("boom", category="test")
class Boom(Operator):
    """总是抛出非框架异常（测错误包装）。"""

    def execute(self, ctx, args):
        raise RuntimeError("kaboom")


@register("badMutator", category="test")
class BadMutator(Operator):
    """违反算子契约：原地修改上游输出（测框架能否发现）。"""

    spec = {"data": Field(list, dynamic=True)}

    def execute(self, ctx, args):
        args["data"].append("oops")
        return args["data"]


@register("badConfigMutator", category="test")
class BadConfigMutator(Operator):
    """违反算子契约：原地修改静态参数——会污染之后所有请求（测框架能否发现）。"""

    spec = {"tags": Field(list, default=[])}

    def execute(self, ctx, args):
        args["tags"].append("oops")
        return args["tags"]
