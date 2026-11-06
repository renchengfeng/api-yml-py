"""frontmatterParse：解析 Markdown / SKILL.md 的 frontmatter。"""
from __future__ import annotations

from typing import Any, Dict

import yaml

from ...errors import BizError
from ...spec import Field
from ..base import Operator
from ..registry import register


@register("frontmatterParse", category="transformer")
class FrontmatterParse(Operator):
    """把 `---` frontmatter 拆成 meta 与 body。"""

    spec = {"content": Field(str, required=True, dynamic=True, desc="带 frontmatter 的文本")}

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        text = args["content"]
        if not text.startswith("---"):
            return {"meta": {}, "body": text}
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise BizError("frontmatter 未闭合", 400)
        try:
            meta = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError as exc:
            raise BizError("frontmatter 解析失败：%s" % exc, 400) from exc
        if not isinstance(meta, dict):
            raise BizError("frontmatter 必须是映射", 400)
        return {"meta": meta, "body": parts[2].lstrip("\r\n")}
