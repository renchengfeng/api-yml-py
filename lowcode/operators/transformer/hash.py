"""hash：计算文本摘要。"""
from __future__ import annotations

import hashlib
from typing import Any, Dict

from ...spec import Field
from ..base import Operator
from ..registry import register


@register("hash", category="transformer")
class Hash(Operator):
    """计算文本的 SHA1 / SHA256 十六进制摘要。"""

    spec = {
        "algorithm": Field(str, default="sha1", choices=("sha1", "sha256"), desc="摘要算法"),
        "content": Field(str, required=True, dynamic=True, desc="待摘要文本"),
    }

    def execute(self, ctx: Any, args: Dict[str, Any]) -> str:
        fn = hashlib.sha1 if args["algorithm"] == "sha1" else hashlib.sha256
        return fn(args["content"].encode("utf-8")).hexdigest()
