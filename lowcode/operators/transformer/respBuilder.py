"""respBuilder：按模板组装输出结构。手册与用例见 operator_md/transformer/respBuilder.md。"""
from __future__ import annotations

from typing import Any, Dict

from ...spec import Field
from ..base import Operator
from ..registry import register


@register("respBuilder", category="transformer")
class RespBuilder(Operator):
    """按模板组装输出结构；通常作为最后一个节点，决定响应 data 的形状。"""

    spec = {
        "data": Field(object, required=True, dynamic=True,
                      desc="任意嵌套的 dict / list / 标量，值支持 {{ }}"),
    }

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        return args["data"]
