"""redisGet：按键读取 Redis 并解析。手册与用例见 operator_md/external/uredis/redisGet.md。

合并了 datamore_lite 的 stringRedisReader / jsonRedisReader / csvRedisReader 三个读取器：
读取方式由 command 决定，值的解析由 format 决定。沿用其"空数据兜底不报错"原则：键不存在时返回 default。
"""
from __future__ import annotations

from typing import Any, Dict

from ....spec import Field
from ...base import Operator
from ...registry import register
from .parse import check_config, parse_value


@register("redisGet", category="external")
class RedisGet(Operator):
    """读取 Redis 键（get / hgetall），按 raw / json / csv 解析。"""

    spec = {
        "dataSource": Field(str, desc="Redis 数据源；缺省取分组 dataSource 或唯一的 kv 数据源"),
        "key": Field(str, required=True, dynamic=True, desc="键名，支持 {{ }}（对应 datamore 的 keyTemplate）"),
        "command": Field(str, default="get", choices=("get", "hgetall")),
        "format": Field(str, default="raw", choices=("raw", "json", "csv"),
                        desc="值的解析方式；hgetall 时作用于每个 field 的值"),
        "delimiter": Field(str, default="|", desc="CSV 列分隔符"),
        "rowDelimiter": Field(str, desc="CSV 行分隔符；设置后返回对象列表，否则返回单个对象"),
        "fields": Field(list, default=[], desc="CSV 列名，按位置对应；缺列补空串"),
        "default": Field(object, desc="键不存在时的返回值"),
    }

    def build(self) -> None:
        self.ds = self.env.datasource(self.config["dataSource"], "kv")
        check_config(self.config, self.config_error)

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        key = args["key"]
        if self.config["command"] == "hgetall":
            data = self.ds.hgetall(key)
            return {k: parse_value(self.config, v, key) for k, v in data.items()} if data else args["default"]
        raw = self.ds.get(key)
        return args["default"] if raw is None else parse_value(self.config, raw, key)
