"""Redis 值的解析与 config 校验：redisGet / redisMGet 共用（raw / json / csv）。

两个算子只差在"读一个键"还是"批量读多个键"，值的解析规则必须只有一份，
否则同一种存储格式在两个算子里解析结果会漂移。
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List

from ....errors import ExecError


def check_config(config: Dict[str, Any], error: Callable[..., Exception]) -> None:
    """按 format 校验 delimiter / fields；error 传算子的 config_error。"""
    if config["format"] != "csv":
        return
    if not config["fields"] or not all(isinstance(f, str) for f in config["fields"]):
        raise error("fields must be a non-empty list of strings when format=csv", "fields")
    if not config["delimiter"] or config["delimiter"] == config["rowDelimiter"]:
        raise error("delimiter must not be empty or equal to rowDelimiter", "delimiter")


def parse_value(config: Dict[str, Any], text: str, key: str) -> Any:
    """按 format 解析一个键的值：raw → 字符串；json → 对象；csv → 对象或对象列表。"""
    fmt = config["format"]
    if fmt == "json":
        try:
            return json.loads(text)
        except ValueError as e:
            raise ExecError(f"value of key {key} is not valid JSON: {e}") from None
    if fmt == "csv":
        if config["rowDelimiter"]:
            return [parse_row(config, line) for line in text.split(config["rowDelimiter"]) if line]
        return parse_row(config, text)
    return text


def parse_row(config: Dict[str, Any], line: str) -> Dict[str, str]:
    """一行 CSV → 对象；列数不足时补空串，保证输出总是包含 fields 的全部列。"""
    cols: List[str] = line.split(config["delimiter"])
    return {f: cols[i] if i < len(cols) else "" for i, f in enumerate(config["fields"])}
