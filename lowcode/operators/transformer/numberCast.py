"""numberCast：把指定字段的字符串转成数值。手册与用例见 operator_md/transformer/numberCast.md。"""
from __future__ import annotations

from typing import Any, Dict

from ...errors import ExecError
from ...spec import Field
from ..base import Operator
from ..registry import register


@register("numberCast", category="transformer")
class NumberCast(Operator):
    """字段数值化：CSV 等文本解析出的 "10" 转成 10，供聚合算子使用。"""

    spec = {
        "data": Field(object, required=True, dynamic=True, desc="对象或对象列表"),
        "fields": Field(list, required=True, desc="要转成数值的字段名；其它字段原样保留"),
    }

    def build(self) -> None:
        if not self.config["fields"] or not all(isinstance(f, str) for f in self.config["fields"]):
            raise self.config_error("fields must be a non-empty list of strings", "fields")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        data = args["data"]
        if isinstance(data, list):
            return [self._cast(row) for row in data]
        if isinstance(data, dict):
            return self._cast(data)
        raise ExecError(f"data must render to an object or a list, got {type(data).__name__}")

    def _cast(self, row: Any) -> Any:
        if not isinstance(row, dict):
            raise ExecError(f"rows to cast must be objects, got {type(row).__name__}")
        out = dict(row)  # 新 dict：不改动上游输出
        for key in self.config["fields"]:
            value = out.get(key)
            if value is None or isinstance(value, (int, float, bool)):
                continue
            if not isinstance(value, str):
                raise ExecError(f"value {value!r} of field {key} is not a string")
            out[key] = self._number(value, key)
        return out

    @staticmethod
    def _number(text: str, key: str) -> Any:
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                raise ExecError(f"value {text!r} of field {key} is not a number") from None
