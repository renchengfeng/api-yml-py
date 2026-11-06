"""textDiff：生成两段文本的 unified diff。"""
from __future__ import annotations

import difflib
from typing import Any, Dict

from ...spec import Field
from ..base import Operator
from ..registry import register


@register("textDiff", category="transformer")
class TextDiff(Operator):
    """返回 left / right 的 unified diff 文本。"""

    spec = {
        "left": Field(str, required=True, dynamic=True, desc="旧文本"),
        "right": Field(str, required=True, dynamic=True, desc="新文本"),
        "fromfile": Field(str, default="left", dynamic=True, desc="旧文件标题"),
        "tofile": Field(str, default="right", dynamic=True, desc="新文件标题"),
        "context": Field(int, default=3, desc="上下文行数"),
    }

    def build(self) -> None:
        if self.config["context"] < 0:
            raise self.config_error("context 不能小于 0", "context")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> str:
        return "".join(difflib.unified_diff(
            args["left"].splitlines(keepends=True),
            args["right"].splitlines(keepends=True),
            fromfile=args["fromfile"],
            tofile=args["tofile"],
            n=args["context"],
        ))
