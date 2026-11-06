"""jsonMerge：对象合并，支持深合并。"""
from __future__ import annotations

from ...errors import BizError
from ...spec import Field
from ..base import Operator
from ..registry import register


def _merge(base, patch, deep: bool):
    if not isinstance(base, dict) or not isinstance(patch, dict):
        return patch
    out = dict(base)
    for key, value in patch.items():
        if deep and key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _merge(out[key], value, True)
        else:
            out[key] = value
    return out


@register("jsonMerge", category="transformer")
class JsonMerge(Operator):
    """把 patch 合并进 base；deep=true 时递归合并对象。"""

    spec = {
        "base": Field(object, required=True, dynamic=True, desc="基础对象"),
        "patch": Field(object, required=True, dynamic=True, desc="覆盖对象"),
        "deep": Field(bool, default=True, desc="是否递归合并对象"),
    }

    def execute(self, ctx, args):
        if not isinstance(args["base"], dict) or not isinstance(args["patch"], dict):
            raise BizError("jsonMerge 的 base / patch 必须是对象", 400)
        return _merge(args["base"], args["patch"], bool(args["deep"]))
