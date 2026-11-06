"""MySQL 数据源（依赖 pymysql；缺包在编译接口时报错，连接延迟到首次调用）。

支持两种 config 写法：
    config: {host: h, port: 3306, user: u, password: p, database: d}
    config: {sourceName: "u:p@tcp(h:3306)/d?charset=utf8mb4&timeout=3s"}   # datamore_lite 风格 DSN

连接池参数（maxOpenConn / maxIdleConn / connMaxLifetime）与 showSQL / retry 为
兼容 datamore_lite 的预留字段：当前实现每次调用新建连接，这些字段仅作声明。
timeout 单位为秒（DSN 里的 3s 会被解析为 3）。
"""
from __future__ import annotations

import re
from importlib.util import find_spec
from typing import Any, Dict, List

from ..errors import ConfigError
from ..spec import Field
from . import DataSource, register_datasource
from .sqltext import to_pyformat

_DSN = re.compile(r"^(?P<user>[^:@]+):(?P<password>[^@]*)@tcp\((?P<host>[^):]+):(?P<port>\d+)\)"
                  r"/(?P<database>[^?]+)(?:\?(?P<params>.*))?$")


@register_datasource("mysql")
class MysqlDataSource(DataSource):
    kind = "sql"
    spec = {
        "host": Field(str, desc="主机；与 sourceName 二选一"),
        "port": Field(int, default=3306),
        "user": Field(str, desc="用户名；与 sourceName 二选一"),
        "password": Field(str, default="", desc="建议写成 ${MYSQL_PASSWORD} 从环境变量注入"),
        "database": Field(str, desc="库名；与 sourceName 二选一"),
        "sourceName": Field(str, desc="datamore 风格 DSN：user:pass@tcp(host:port)/db?charset=utf8mb4&timeout=3s"),
        "charset": Field(str, default="utf8mb4"),
        "timeout": Field((int, float), default=5, desc="连接 / 读写超时（秒）"),
        "maxOpenConn": Field(int, desc="预留：当前实现每次调用新建连接"),
        "maxIdleConn": Field(int, desc="预留"),
        "connMaxLifetime": Field(int, desc="预留（秒）"),
        "showSQL": Field(bool, default=False, desc="预留"),
        "retry": Field(int, default=3, desc="预留"),
    }

    def check(self) -> None:
        """解析并校验连接信息；连接延迟到首次调用。"""
        c = self.config
        self._conn: Dict[str, Any] = {"charset": c["charset"],
                                      "connect_timeout": c["timeout"],
                                      "read_timeout": c["timeout"],
                                      "write_timeout": c["timeout"]}
        if c["sourceName"]:
            m = _DSN.match(c["sourceName"])
            if not m:
                raise ConfigError("invalid sourceName DSN, expected user:pass@tcp(host:port)/db?params",
                                  child(self.where, "sourceName"))
            d = m.groupdict()
            self._conn.update(host=d["host"], port=int(d["port"]), user=d["user"],
                              password=d["password"], database=d["database"])
            if c["timeout"] == 5 and d["params"]:  # DSN 里的 timeout 优先于默认值
                for p in d["params"].split("&"):
                    k, _, v = p.partition("=")
                    if k == "timeout" and v.endswith("s"):
                        self._conn["connect_timeout"] = self._conn["read_timeout"] = \
                            self._conn["write_timeout"] = float(v[:-1])
        elif c["host"] and c["user"] and c["database"]:
            self._conn.update(host=c["host"], port=c["port"], user=c["user"],
                              password=c["password"], database=c["database"])
        else:
            raise ConfigError("set sourceName, or host / user / database together", self.where)
    def check_dependencies(self) -> None:
        """pymysql 缺失时抛错：编译使用本数据源的接口时触发，启动期即暴露。"""
        if find_spec("pymysql") is None:
            raise ConfigError('mysql datasource requires pymysql: pip install "api-yml-py[mysql]"', self.where)

    def _connect(self):
        try:
            import pymysql
        except ImportError:
            raise ConfigError('mysql datasource requires pymysql: pip install "api-yml-py[mysql]"', self.where) from None
        return pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **self._conn)

    def query(self, sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(to_pyformat(sql), params)
                return list(cur.fetchall())
        finally:
            conn.close()

    def execute(self, sql: str, params: Dict[str, Any]) -> Dict[str, Any]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                rowcount = cur.execute(to_pyformat(sql), params)
                conn.commit()
                return {"rowcount": rowcount, "lastrowid": cur.lastrowid or None}  # 非 INSERT 为 0，统一为 None
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
