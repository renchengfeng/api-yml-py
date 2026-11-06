"""jsonStringify：对象转 JSON 文本。"""
from __future__ import annotations

import json

from ...spec import Field
from ..base import Operator
from ..registry import register


@register("jsonStringify", category="transformer")
class JsonStringify(Operator):
    """把对象序列化为 JSON 文本。"""

    spec = {
        "data": Field(object, required=True, dynamic=True, desc="任意可序列化对象"),
        "indent": Field(int, default=0, desc="缩进空格数，0 表示紧凑"),
    }

    def execute(self, ctx, args):
        return json.dumps(args["data"], ensure_ascii=False, indent=args["indent"] or None,
                          separators=(",", ":") if not args["indent"] else None)
