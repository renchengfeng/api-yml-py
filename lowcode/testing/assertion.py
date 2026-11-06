"""输出断言：类型 + 值的严格比较（对应 datamore_lite testhelper 的 assertExpect）。

为什么不直接用 ==：Python 中 True == 1、[1] == [True]，"1" 与 1 的差异也可能被宽松比较掩盖。
这里按 JSON 的类型类别比较：null / 布尔 / 数字 / 字符串 / 列表 / 对象 互不相等；
int 与 float 同属"数字"（与 JSON 一致），tuple 视同列表，对象不比较键的顺序。
不一致时报出第一处差异的路径，如 output.list[0].id: 期望 1（数字），实际 '1'（字符串）。
"""
from __future__ import annotations

from typing import Any, Optional


def _category(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, (list, tuple)):
        return "list"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def first_diff(actual: Any, expected: Any, path: str = "output") -> Optional[str]:
    """返回第一处差异的描述；完全一致时返回 None。"""
    ca, ce = _category(actual), _category(expected)
    if ca != ce:
        return f"{path}: expected {expected!r} ({ce}), got {actual!r} ({ca})"
    if ca == "list":
        if len(actual) != len(expected):
            return f"{path}: expected {len(expected)} items, got {len(actual)}"
        for i, (a, e) in enumerate(zip(actual, expected)):
            diff = first_diff(a, e, f"{path}[{i}]")
            if diff:
                return diff
        return None
    if ca == "object":
        missing = [k for k in expected if k not in actual]
        extra = [k for k in actual if k not in expected]
        if missing or extra:
            return f"{path}: missing keys {missing}, extra keys {extra}"
        for k in expected:
            diff = first_diff(actual[k], expected[k], f"{path}.{k}")
            if diff:
                return diff
        return None
    if actual != expected:
        return f"{path}: expected {expected!r}, got {actual!r}"
    return None
