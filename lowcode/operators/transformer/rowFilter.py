"""rowFilter：按字段与阈值的比较结果过滤行。手册与用例见 operator_md/transformer/rowFilter.md。"""
from __future__ import annotations

import operator
from typing import Any, Dict

from ...errors import ExecError
from ...spec import Field
from ..base import Operator
from ..registry import register

_OPS = {
    "gt": operator.gt, "gte": operator.ge, "lt": operator.lt,
    "lte": operator.le, "eq": operator.eq, "ne": operator.ne,
}


@register("rowFilter", category="transformer")
class RowFilter(Operator):
    """按单个字段的比较结果保留对象列表中的行；不中断流程，也不修改上游数据。"""

    spec = {
        "data": Field(list, required=True, dynamic=True, desc="对象列表"),
        "field": Field(str, required=True, desc="参与比较的字段；缺失该字段的行不保留"),
        "op": Field(str, default="gt", choices=tuple(_OPS), desc="比较运算符"),
        "value": Field(object, required=True, dynamic=True, desc="阈值，支持 {{ }}"),
    }

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        rows = args["data"]
        if not isinstance(rows, list):
            raise ExecError(f"data must render to a list, got {type(rows).__name__}")
        field, compare, threshold = self.config["field"], _OPS[self.config["op"]], args["value"]
        kept = []
        for row in rows:
            if not isinstance(row, dict):
                raise ExecError(f"rows to filter must be objects, got {type(row).__name__}")
            value = row.get(field)
            if value is None:
                continue
            try:
                match = compare(value, threshold)
            except TypeError as e:
                raise ExecError(f"cannot compare field {field}={value!r} with value {threshold!r}: {e}") from None
            if match:
                kept.append(row)
        return kept
