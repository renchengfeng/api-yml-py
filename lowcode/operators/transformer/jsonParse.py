"""jsonParse：JSON 文本转对象。"""
from __future__ import annotations

import json

from ...errors import BizError
from ...spec import Field
from ..base import Operator
from ..registry import register


@register("jsonParse", category="transformer")
class JsonParse(Operator):
    """把 JSON 文本解析成对象。"""

    spec = {"content": Field(str, required=True, dynamic=True, desc="JSON 文本")}

    def execute(self, ctx, args):
        try:
            return json.loads(args["content"])
        except (TypeError, ValueError) as exc:
            raise BizError("JSON 解析失败：%s" % exc, 400) from exc
