"""sqlExec：在事务中执行写 SQL。手册与用例见 operator_md/external/usql/sqlExec.md。"""
from __future__ import annotations

from typing import Any, Dict

from .base import _SPEC, _SqlOperator
from ...registry import register


@register("sqlExec", category="external")
class SqlExec(_SqlOperator):
    """执行写 SQL（事务内），返回 {rowcount, lastrowid}。"""

    allowed = ("insert", "update", "delete", "replace")
    spec = dict(_SPEC)

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        return self.ds.execute(self.config["sql"], self._params(args))
