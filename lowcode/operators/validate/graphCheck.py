"""graphCheck：通用图结构校验。"""
from __future__ import annotations

from typing import Any, Dict, List

from ...errors import BizError
from ...spec import Field
from ..base import Operator
from ..registry import register


@register("graphCheck", category="validate")
class GraphCheck(Operator):
    """校验节点唯一、边端点存在、可选无环。"""

    spec = {
        "nodes": Field(list, required=True, dynamic=True, desc="节点列表"),
        "edges": Field(list, required=True, dynamic=True, desc="边列表"),
        "idField": Field(str, default="id", desc="节点 id 字段"),
        "fromField": Field(str, default="from", desc="边起点字段"),
        "toField": Field(str, default="to", desc="边终点字段"),
        "allowCycles": Field(bool, default=False, desc="是否允许环"),
    }

    def execute(self, ctx, args):
        errors: List[Dict[str, Any]] = []
        ids = set()
        for idx, node in enumerate(args["nodes"]):
            if not isinstance(node, dict) or not node.get(args["idField"]):
                errors.append({"path": "nodes[%d]" % idx, "message": "缺少 id"})
                continue
            nid = str(node[args["idField"]])
            if nid in ids:
                errors.append({"path": nid, "message": "节点 id 重复"})
            ids.add(nid)
        adjacency: Dict[str, List[str]] = {nid: [] for nid in ids}
        for idx, edge in enumerate(args["edges"]):
            if not isinstance(edge, dict):
                errors.append({"path": "edges[%d]" % idx, "message": "边必须是对象"})
                continue
            src, dst = str(edge.get(args["fromField"]) or ""), str(edge.get(args["toField"]) or "")
            if src not in ids:
                errors.append({"path": "edges[%d]" % idx, "message": "起点不存在：%s" % src})
            if dst not in ids:
                errors.append({"path": "edges[%d]" % idx, "message": "终点不存在：%s" % dst})
            if src in adjacency and dst in ids:
                adjacency[src].append(dst)
        if not errors and not args["allowCycles"]:
            visiting, done = set(), set()
            def visit(nid: str) -> bool:
                if nid in visiting:
                    return False
                if nid in done:
                    return True
                visiting.add(nid)
                for nxt in adjacency.get(nid, []):
                    if not visit(nxt):
                        return False
                visiting.remove(nid); done.add(nid)
                return True
            for nid in ids:
                if not visit(nid):
                    errors.append({"path": "$", "message": "检测到环"})
                    break
        return {"ok": not errors, "errors": errors, "nodeCount": len(ids), "edgeCount": len(args["edges"])}
