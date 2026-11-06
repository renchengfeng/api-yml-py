"""yamlParse：YAML 文本转对象。"""
from __future__ import annotations

from typing import Any, Dict

import yaml

from ...errors import BizError
from ...spec import Field
from ..base import Operator
from ..registry import register


@register("yamlParse", category="transformer")
class YamlParse(Operator):
    """把 YAML 文本解析成对象。"""

    spec = {"content": Field(str, required=True, dynamic=True, desc="YAML 文本")}

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        try:
            return yaml.safe_load(args["content"])
        except yaml.YAMLError as exc:
            raise BizError("YAML 解析失败：%s" % exc, 400) from exc
