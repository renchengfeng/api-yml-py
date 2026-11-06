"""redisMGet：一次批量读取多个键。手册与用例见 operator_md/external/uredis/redisMGet.md。"""
from __future__ import annotations

from typing import Any, Dict, List

from ....errors import ExecError
from ....spec import Field
from ...base import Operator
from ...registry import register
from .parse import check_config, parse_value


@register("redisMGet", category="external")
class RedisMGet(Operator):
    """批量读取多个键（一次 MGET），按键顺序把解析结果拼成一个列表。"""

    spec = {
        "dataSource": Field(str, desc="Redis 数据源；缺省取分组 dataSource 或唯一的 kv 数据源"),
        "keys": Field(list, required=True, dynamic=True,
                      desc="键名列表，支持 {{ }}（可用列表拼接，如 {{ keysA + keysB }}）"),
        "format": Field(str, default="raw", choices=("raw", "json", "csv"), desc="每个值的解析方式"),
        "delimiter": Field(str, default="|", desc="CSV 列分隔符"),
        "rowDelimiter": Field(str, desc="CSV 行分隔符；设置后每个键展开为多行"),
        "fields": Field(list, default=[], desc="CSV 列名，按位置对应；缺列补空串"),
        "skipMissing": Field(bool, default=True, desc="键不存在时跳过；false 时用 default 占位"),
        "default": Field(object, desc="skipMissing=false 时，键不存在的占位值"),
    }

    def build(self) -> None:
        self.ds = self.env.datasource(self.config["dataSource"], "kv")
        check_config(self.config, self.config_error)

    def execute(self, ctx: Any, args: Dict[str, Any]) -> List[Any]:
        keys = args["keys"]
        if not isinstance(keys, list):
            raise ExecError(f"keys must render to a list, got {type(keys).__name__}")
        if not all(isinstance(k, str) for k in keys):
            raise ExecError("keys must be a list of strings")
        if not keys:
            return []
        out: List[Any] = []
        for key, raw in zip(keys, self.ds.mget(keys)):
            if raw is None:
                if not self.config["skipMissing"]:
                    out.append(args["default"])
                continue
            value = parse_value(self.config, raw, key)
            # CSV 多行会把一个键展开成多行：直接拼接，下游（groupBy 等）拿到的就是一张表
            if isinstance(value, list):
                out.extend(value)
            else:
                out.append(value)
        return out
