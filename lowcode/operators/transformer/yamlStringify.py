"""yamlStringify：对象转 YAML 文本。"""
from __future__ import annotations

from typing import Any, Dict

import yaml

from ...spec import Field
from ..base import Operator
from ..registry import register


@register("yamlStringify", category="transformer")
class YamlStringify(Operator):
    """把对象序列化为 YAML 文本。"""

    spec = {"data": Field(object, required=True, dynamic=True, desc="任意可序列化对象")}

    def execute(self, ctx: Any, args: Dict[str, Any]) -> str:
        return yaml.safe_dump(args["data"], allow_unicode=True, sort_keys=False, width=120)
