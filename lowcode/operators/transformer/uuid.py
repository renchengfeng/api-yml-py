"""uuid：生成带前缀的唯一标识。"""
from __future__ import annotations

import uuid as _uuid

from ...spec import Field
from ..base import Operator
from ..registry import register


@register("uuid", category="transformer")
class Uuid(Operator):
    """返回 prefix + 随机 hex；提供 value 时返回固定值，便于测试。"""

    spec = {
        "prefix": Field(str, default="", desc="前缀"),
        "value": Field(str, default="", dynamic=True, desc="固定值；为空时随机生成"),
        "length": Field(int, default=12, desc="随机 hex 长度"),
    }

    def execute(self, ctx, args):
        if args["value"]:
            return str(args["prefix"]) + str(args["value"])
        size = max(1, int(args["length"]))
        return str(args["prefix"]) + _uuid.uuid4().hex[:size]
