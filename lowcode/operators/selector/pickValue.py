"""pickValue：根据布尔条件选择一个值。"""
from __future__ import annotations

from ...spec import Field
from ..base import Operator
from ..registry import register


@register("pickValue", category="selector")
class PickValue(Operator):
    """条件值选择；不执行子图，只返回 whenTrue / whenFalse。"""

    spec = {
        "condition": Field(bool, required=True, dynamic=True, desc="条件"),
        "whenTrue": Field(object, default=None, dynamic=True, desc="条件为真时的值"),
        "whenFalse": Field(object, default=None, dynamic=True, desc="条件为假时的值"),
    }

    def execute(self, ctx, args):
        return args["whenTrue"] if args["condition"] else args["whenFalse"]
