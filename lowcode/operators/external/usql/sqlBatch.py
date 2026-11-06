"""sqlBatch：在一个事务中执行多条写 SQL。"""
from __future__ import annotations

from typing import Any, Dict

from ....datasources.sqltext import bind_names, leading_keyword
from ....errors import ConfigError
from ....spec import Field
from ...base import Operator
from ...registry import register


@register("sqlBatch", category="external")
class SqlBatch(Operator):
    """在数据源事务中执行多条写 SQL。"""

    spec = {
        "dataSource": Field(str, desc="SQL 数据源名"),
        "statements": Field(list, required=True, dynamic=True,
                            desc="[{sql: ..., params: {...}}]"),
    }

    def build(self) -> None:
        self.ds = self.env.datasource(self.config["dataSource"], "sql")
        if not isinstance(self.config["statements"], list):
            return
        for idx, item in enumerate(self.config["statements"]):
            if not isinstance(item, dict) or not item.get("sql"):
                raise self.config_error("statements[%d] 缺少 sql" % idx, "statements")
            sql = str(item["sql"])
            if leading_keyword(sql) not in ("insert", "update", "delete", "replace"):
                raise self.config_error("sqlBatch 只接受写 SQL", "statements")
            params = item.get("params") or {}
            if isinstance(params, dict):
                names = bind_names(sql)
                if [n for n in names if n not in params]:
                    raise self.config_error("statements[%d] 缺少绑定参数" % idx, "statements")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        statements = args["statements"]
        if not isinstance(statements, list):
            raise ConfigError("statements 渲染结果必须是列表")
        results = self.ds.transaction(statements)
        return {"results": results}
