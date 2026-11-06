"""SQLite 数据源（标准库，零依赖）。"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import Any, Dict, List

from ..errors import ConfigError
from ..spec import Field, child
from . import DataSource, register_datasource


@register_datasource("sqlite")
class SqliteDataSource(DataSource):
    """每次调用新建连接：SQLite 建连极轻，且避免了跨线程共享连接的问题。"""

    kind = "sql"
    spec = {
        "path": Field(str, required=True, desc="数据库文件，相对 server.yaml 所在目录"),
        "readonly": Field(bool, default=False, desc="只读打开，防止配置误写库"),
    }

    def check(self) -> None:
        self.path = (self.root / self.config["path"]).resolve()
        # 文件不存在时 sqlite 会悄悄建一个空库 —— 相对路径写错时极难排查，这里直接报错
        if not self.path.is_file():
            raise ConfigError(f"database file not found: {self.path}", child(self.where, "path"))
        self._uri = self.path.as_uri() + ("?mode=ro" if self.config["readonly"] else "")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._uri, uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def query(self, sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        with closing(self._connect()) as conn:
            return [dict(row) for row in conn.execute(sql, params)]

    def execute(self, sql: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # 第二个 conn 是事务上下文：成功提交，异常回滚
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(sql, params)
            # 非 INSERT 时 lastrowid 在不同 Python 版本下是 None 或 0，统一为 None
            return {"rowcount": cur.rowcount, "lastrowid": cur.lastrowid or None}
