"""schemaValidate：轻量 JSON Schema 子集校验。"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from ...spec import Field
from ..base import Operator
from ..registry import register


_TYPES = {
    "object": dict, "array": list, "string": str,
    "integer": int, "number": (int, float), "boolean": bool, "null": type(None),
}


class _Errors:
    def __init__(self):
        self.items: List[Dict[str, Any]] = []

    def add(self, path: str, message: str) -> None:
        self.items.append({"path": path or "$", "message": message})


def _check(value: Any, schema: Dict[str, Any], path: str, errors: _Errors) -> None:
    if not isinstance(schema, dict):
        errors.add(path, "schema 必须是对象")
        return
    typ = schema.get("type")
    if typ:
        expected = _TYPES.get(typ)
        if expected is not None and not isinstance(value, expected):
            errors.add(path, "应为 %s" % typ)
            return
    if "enum" in schema and value not in schema["enum"]:
        errors.add(path, "不在枚举范围内")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.add(path, "长度小于 %s" % schema["minLength"])
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.add(path, "长度大于 %s" % schema["maxLength"])
        if "pattern" in schema and not re.search(str(schema["pattern"]), value):
            errors.add(path, "不匹配 pattern")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.add(path, "小于 minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.add(path, "大于 maximum")
    if isinstance(value, dict):
        for key in schema.get("required") or []:
            if key not in value:
                errors.add("%s.%s" % (path, key), "缺少必填字段")
        props = schema.get("properties") or {}
        for key, child in props.items():
            if key in value:
                _check(value[key], child, "%s.%s" % (path, key), errors)
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(props)
            for key in sorted(extra):
                errors.add("%s.%s" % (path, key), "不允许的字段")
    if isinstance(value, list) and schema.get("items"):
        for idx, item in enumerate(value):
            _check(item, schema["items"], "%s[%s]" % (path, idx), errors)


@register("schemaValidate", category="validate")
class SchemaValidate(Operator):
    """校验 JSON Schema 子集：type / required / properties / items / enum / pattern / 长度 / 数值范围。"""

    spec = {
        "data": Field(object, required=True, dynamic=True, desc="待校验数据"),
        "schema": Field(object, required=True, desc="JSON Schema 子集"),
    }

    def execute(self, ctx, args):
        errors = _Errors()
        _check(args["data"], args["schema"], "$", errors)
        return {"ok": not errors.items, "errors": errors.items}
