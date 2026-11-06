"""pickPaths：按点号路径投影对象字段。"""
from __future__ import annotations

from typing import Any, Dict

from ...spec import Field
from ..base import Operator
from ..registry import register


def _get(value: Any, path: str) -> Any:
    cur = value
    for part in str(path or "").split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


@register("pickPaths", category="transformer")
class PickPaths(Operator):
    """按输出字段到源路径的映射投影对象或对象列表。"""

    spec = {
        "data": Field(object, required=True, dynamic=True, desc="对象或对象列表"),
        "fields": Field(object, required=True, desc="输出字段 -> 源路径，如 id: data.id"),
    }

    def build(self) -> None:
        fields = self.config["fields"]
        if not fields or not all(isinstance(k, str) and isinstance(v, str) for k, v in fields.items()):
            raise self.config_error("fields 必须是 输出字段 -> 源路径 的字符串映射", "fields")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        fields = args["fields"]
        data = args["data"]
        if isinstance(data, list):
            return [{out: _get(row, path) for out, path in fields.items()} for row in data]
        return {out: _get(data, path) for out, path in fields.items()}
