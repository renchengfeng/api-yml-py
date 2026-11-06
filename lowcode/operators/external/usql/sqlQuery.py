"""sqlQuery：执行查询 SQL。手册与用例见 operator_md/external/usql/sqlQuery.md。"""
from __future__ import annotations

from typing import Any, Dict

from ....spec import Field
from .base import _SPEC, _SqlOperator
from ...registry import register


@register("sqlQuery", category="external")
class SqlQuery(_SqlOperator):
    """执行查询 SQL，返回行列表；single=true 时返回首行（无数据为 null）。"""

    allowed = ("select", "with")
    spec = {**_SPEC, "single": Field(bool, default=False, desc="只取首行")}

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        rows = self.ds.query(self.config["sql"], self._params(args))
        if self.config["single"]:
            return rows[0] if rows else None
        return rows
