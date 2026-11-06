"""sortList：按字段排序对象列表。"""
from __future__ import annotations

from typing import Any, Dict, List

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


@register("sortList", category="transformer")
class SortList(Operator):
    """按点号路径字段排序对象列表。"""

    spec = {
        "data": Field(list, required=True, dynamic=True, desc="对象列表"),
        "field": Field(str, required=True, desc="排序字段，支持 data.updated_at"),
        "desc": Field(bool, default=False, desc="是否降序"),
        "missing": Field(str, default="last", choices=("first", "last"), desc="缺失值位置"),
    }

    def build(self) -> None:
        if not self.config["field"].strip():
            raise self.config_error("field 不能为空", "field")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> List[Any]:
        rows = list(args["data"])
        missing_rank = 0 if args["missing"] == "first" else 1

        def key(row: Any):
            value = _get(row, args["field"])
            rank = missing_rank if value is None else 0
            return rank, value if value is not None else ""

        try:
            return sorted(rows, key=key, reverse=bool(args["desc"]))
        except TypeError:
            return sorted(rows, key=lambda row: (key(row)[0], str(key(row)[1])), reverse=bool(args["desc"]))
