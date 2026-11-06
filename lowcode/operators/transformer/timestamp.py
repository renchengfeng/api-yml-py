"""timestamp：生成时间字符串。"""
from __future__ import annotations

from datetime import datetime

from ...spec import Field
from ..base import Operator
from ..registry import register


@register("timestamp", category="transformer")
class Timestamp(Operator):
    """返回当前时间；提供 value 时返回固定值，便于测试。"""

    spec = {
        "format": Field(str, default="%Y-%m-%dT%H:%M:%S", desc="strftime 格式"),
        "value": Field(str, default="", dynamic=True, desc="固定值；为空时取当前时间"),
    }

    def execute(self, ctx, args):
        return str(args["value"]) if args["value"] else datetime.now().strftime(args["format"])
