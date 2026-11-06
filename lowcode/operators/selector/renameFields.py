"""renameFields：按映射重命名字段。手册与用例见 operator_md/selector/renameFields.md。"""
from __future__ import annotations

from typing import Any, Dict

from ...errors import ExecError
from ...spec import Field
from ..base import Operator
from ..registry import register


@register("renameFields", category="selector")
class RenameFields(Operator):
    """按映射重命名字段：对象或对象列表，未列出的字段保持原名。"""

    spec = {
        "data": Field(object, required=True, dynamic=True, desc="对象或对象列表"),
        "mapping": Field(dict, required=True, desc="旧字段名 → 新字段名，如 {sum: cnt}"),
    }

    def build(self) -> None:
        mapping = self.config["mapping"]
        if not mapping:
            raise self.config_error("mapping must not be empty", "mapping")
        for old, new in mapping.items():
            if not isinstance(old, str) or not isinstance(new, str) or not new:
                raise self.config_error(f"mapping must map field names to non-empty strings, "
                                        f"got {old!r}: {new!r}", "mapping")
        targets = list(mapping.values())
        if len(set(targets)) != len(targets):
            raise self.config_error("mapping has duplicate target names", "mapping")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        data = args["data"]
        if isinstance(data, list):
            return [self._rename(row) for row in data]
        if isinstance(data, dict):
            return self._rename(data)
        raise ExecError(f"data must render to an object or a list, got {type(data).__name__}")

    def _rename(self, row: Any) -> Dict[str, Any]:
        if not isinstance(row, dict):
            raise ExecError(f"rows to rename must be objects, got {type(row).__name__}")
        mapping = self.config["mapping"]
        out: Dict[str, Any] = {}
        for key, value in row.items():
            name = mapping.get(key, key)
            if name in out:  # 目标字段已存在：报错，不静默覆盖
                raise ExecError(f"cannot rename {key!r} to {name!r}: field {name!r} already exists")
            out[name] = value
        return out
