"""groupBy：按字段分组统计。手册与用例见 operator_md/aggregate/groupBy.md。"""
from __future__ import annotations

from typing import Any, Dict, List

from ...errors import ExecError
from ...spec import Field
from ..base import Operator
from ..registry import register
from .stats import check_ops, stats


@register("groupBy", category="aggregate")
class GroupBy(Operator):
    """按字段分组统计，输出 [{<by>: key, count, ...}]；按 key 升序，结果顺序稳定。"""

    spec = {
        "data": Field(list, required=True, dynamic=True, desc="对象列表"),
        "by": Field(str, required=True, desc="分组字段；缺失该字段的行归入 null 组"),
        "field": Field(str, desc="数值字段；ops 只有 count 时可省略"),
        "ops": Field(list, default=["count"], desc="组内统计项，按声明顺序输出"),
    }

    def build(self) -> None:
        check_ops(self.config["ops"], self.config["field"], self.env.where)

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        data = args["data"]
        if not isinstance(data, list):
            raise ExecError(f"data must render to a list, got {type(data).__name__}")
        by = self.config["by"]
        groups: Dict[Any, List[Any]] = {}
        for row in data:
            if not isinstance(row, dict):
                raise ExecError(f"统计的行应为对象，实际是 {type(row).__name__}")
            groups.setdefault(row.get(by), []).append(row)
        # datamore_lite 的白盒报告指出 map 遍历顺序随机会导致结果不稳定，
        # 这里固定按 key 升序（null 组最前），同类 key 值聚合结果可预期。
        keys = sorted(groups, key=lambda k: (k is not None, str(k)))
        return [{by: key, **stats(groups[key], self.config["field"], self.config["ops"])} for key in keys]
