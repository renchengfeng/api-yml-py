"""listAgg：对对象列表做整体统计。手册与用例见 operator_md/aggregate/listAgg.md。"""
from __future__ import annotations

from typing import Any, Dict

from ...errors import ExecError
from ...spec import Field
from ..base import Operator
from ..registry import register
from .stats import check_ops, stats


@register("listAgg", category="aggregate")
class ListAgg(Operator):
    """对对象列表的数值字段做统计，返回 {count, sum, ...}。"""

    spec = {
        "data": Field(list, required=True, dynamic=True, desc="对象列表"),
        "field": Field(str, desc="数值字段；ops 只有 count 时可省略"),
        "ops": Field(list, default=["count", "sum", "avg", "min", "max"], desc="统计项，按声明顺序输出"),
    }

    def build(self) -> None:
        check_ops(self.config["ops"], self.config["field"], self.env.where)

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        data = args["data"]
        if not isinstance(data, list):
            raise ExecError(f"data must render to a list, got {type(data).__name__}")
        return stats(data, self.config["field"], self.config["ops"])
