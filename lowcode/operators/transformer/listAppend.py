"""listAppend：向列表追加一个元素。"""
from __future__ import annotations

from ...spec import Field
from ..base import Operator
from ..registry import register


@register("listAppend", category="transformer")
class ListAppend(Operator):
    """返回 data + [item]，不修改原列表。"""

    spec = {
        "data": Field(list, required=True, dynamic=True, desc="原列表"),
        "item": Field(object, required=True, dynamic=True, desc="追加元素"),
    }

    def execute(self, ctx, args):
        return list(args["data"]) + [args["item"]]
