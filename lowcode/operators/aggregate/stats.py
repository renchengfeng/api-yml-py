"""聚合算子的公共部分：数值提取与统计（listAgg / groupBy 共用）。"""
from __future__ import annotations

from typing import Any, Dict, List

from ...errors import ConfigError, ExecError
from ...spec import child

OPS = ("count", "sum", "avg", "min", "max")  # count 不需要数值字段


def check_ops(ops: List[str], field: str, where: str) -> None:
    """启动期校验 ops；count 之外的操作必须提供数值字段。"""
    at_ops, at_field = child(where, "ops"), child(where, "field")
    if not ops:
        raise ConfigError(f"ops must not be empty (available: {', '.join(OPS)})", at_ops)
    unknown = [op for op in ops if op not in OPS]
    if unknown:
        raise ConfigError(f"unknown stats op {unknown[0]!r} (available: {', '.join(OPS)})", at_ops)
    if len(set(ops)) != len(ops):
        raise ConfigError("duplicate entries in ops", at_ops)
    if set(ops) - {"count"} and not field:
        raise ConfigError("field is required when ops includes anything other than count", at_field)


def numbers(rows: List[Any], field: str) -> List[float]:
    """提取数值字段：缺失 / null 的行跳过；bool 与非数值视为配置错误（显式报错好过静默丢数）。"""
    values: List[float] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ExecError(f"rows to aggregate must be objects, got {type(row).__name__}")
        v = row.get(field)
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ExecError(f"value {v!r} of field {field} is not a number (bool/str are not aggregated)")
        values.append(v)
    return values


def stats(rows: List[Any], field: str, ops: List[str]) -> Dict[str, Any]:
    """按 ops 计算统计值。空数据兜底不报错：sum=0，avg / min / max=null（沿用 datamore 原则）。"""
    values = numbers(rows, field) if set(ops) - {"count"} else []
    out: Dict[str, Any] = {}
    for op in ops:
        if op == "count":
            out[op] = len(rows)
        elif not values:
            out[op] = 0 if op == "sum" else None
        elif op == "sum":
            out[op] = sum(values)
        elif op == "avg":
            out[op] = round(sum(values) / len(values), 4)
        elif op == "min":
            out[op] = min(values)
        else:
            out[op] = max(values)
    return out
