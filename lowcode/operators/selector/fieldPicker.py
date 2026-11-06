"""fieldPicker：字段投影。手册与用例见 operator_md/selector/fieldPicker.md。"""
from __future__ import annotations

from typing import Any, Dict

from ...spec import Field
from ..base import Operator
from ..registry import register


@register("fieldPicker", category="selector")
class FieldPicker(Operator):
    """从对象或对象列表中挑选字段；缺失字段补 null，输出结构稳定。"""

    spec = {
        "data": Field(object, required=True, dynamic=True, desc="对象或对象列表"),
        "fields": Field(list, required=True, desc="保留的字段，按声明顺序输出"),
    }

    def build(self) -> None:
        if not self.config["fields"] or not all(isinstance(f, str) for f in self.config["fields"]):
            raise self.config_error("fields must be a non-empty list of strings", "fields")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        data = args["data"]
        if isinstance(data, list):
            return [self._pick(row) for row in data]
        return self._pick(data)

    def _pick(self, row: Any) -> Any:
        if not isinstance(row, dict):
            return row  # null 等非对象原样透传
        return {f: row.get(f) for f in self.config["fields"]}  # 新 dict：不改动上游
