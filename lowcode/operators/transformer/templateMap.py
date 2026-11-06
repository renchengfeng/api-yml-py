"""templateMap：把列表按模板逐项渲染成新列表。手册与用例见 operator_md/transformer/templateMap.md。"""
from __future__ import annotations

from typing import Any, Dict, List

from ...errors import ExecError
from ...spec import Field, child
from ..base import Operator
from ..registry import register


@register("templateMap", category="transformer")
class TemplateMap(Operator):
    """把列表按模板逐项渲染成新列表；模板里可用 item / index。"""

    spec = {
        "items": Field(list, required=True, dynamic=True, desc="待映射的列表，通常是上游节点输出"),
        "template": Field(str, required=True, raw=True,
                          desc="逐项渲染的模板，可用 {{ item }} / {{ index }}；由本算子渲染，框架不预编译"),
    }

    def build(self) -> None:
        # 延迟导入：core 依赖 operators（builder 取算子），这里反向引用 core.template 需避开导入环
        from ...core.template import compile_template
        where = child(child(self.env.where, "config"), "template")
        self.tpl = compile_template(self.config["template"], where)

    def execute(self, ctx: Any, args: Dict[str, Any]) -> List[Any]:
        items = args["items"]
        if not isinstance(items, list):
            raise ExecError(f"items must render to a list, got {type(items).__name__}")
        scope = ctx.scope()  # 副本：写入 item / index 不影响其它节点
        out: List[Any] = []
        for index, item in enumerate(items):
            scope["item"] = item
            scope["index"] = index
            out.append(self.tpl.render(scope))
        return out
