"""ruleCheck：声明式数据规则校验。"""
from __future__ import annotations

from typing import Any, Dict, List

from ...spec import Field
from ..base import Operator
from ..registry import register


def _values(data: Any, path: str) -> List[Any]:
    cur = [data]
    for part in str(path or "").split("."):
        if not part:
            continue
        nxt = []
        for item in cur:
            if part == "*":
                if isinstance(item, list):
                    nxt.extend(item)
                elif isinstance(item, dict):
                    nxt.extend(item.values())
            elif isinstance(item, dict):
                if part in item:
                    nxt.append(item[part])
            elif isinstance(item, list) and part.isdigit() and int(part) < len(item):
                nxt.append(item[int(part)])
        cur = nxt
    return cur


def _first(data: Any, path: str) -> Any:
    values = _values(data, path)
    return values[0] if values else None


def _flatten(values: List[Any]) -> List[str]:
    out = []
    for value in values:
        if value is None or value == "":
            continue
        if isinstance(value, (list, tuple, set)):
            out.extend(str(x) for x in value)
        else:
            out.append(str(value))
    return out


def _target_ids(rule: Dict[str, Any], data: Any, context: Dict[str, Any]) -> List[str]:
    if "targetPath" in rule:
        return _flatten(_values(data, rule["targetPath"]))
    target = context.get(rule.get("target"))
    if target is None:
        target = rule.get("target")
    if isinstance(target, list):
        if rule.get("targetField"):
            return _flatten([x.get(rule["targetField"]) if isinstance(x, dict) else x for x in target])
        return _flatten(target)
    return []


@register("ruleCheck", category="validate")
class RuleCheck(Operator):
    """按声明式规则校验对象；支持 unique/countWhere/refExists/relatedForbidden。"""

    spec = {
        "data": Field(object, required=True, dynamic=True, desc="待校验对象"),
        "context": Field(object, default={}, dynamic=True, desc="外部 ID 集合，如 skillIds"),
        "rules": Field(list, required=True, dynamic=True, desc="规则列表"),
    }

    def execute(self, ctx, args):
        data = args["data"]
        context = args["context"] or {}
        errors: List[Dict[str, Any]] = []
        for idx, rule in enumerate(args["rules"]):
            if not isinstance(rule, dict):
                errors.append({"rule": idx, "message": "规则必须是对象"})
                continue
            check = rule.get("check")
            path = rule.get("path") or rule.get("from") or ""
            values = _values(data, path) if path else []
            if check == "unique":
                flat = _flatten(values)
                if len(flat) != len(set(flat)):
                    errors.append({"rule": idx, "path": path, "message": rule.get("message", "值不唯一")})
            elif check == "countWhere":
                rows = _first(data, rule.get("collection", "")) if rule.get("collection") else values
                rows = rows if isinstance(rows, list) else []
                matched = [x for x in rows if isinstance(x, dict) and x.get(rule.get("field")) == rule.get("equals")]
                if len(matched) != int(rule.get("count", 0)):
                    errors.append({"rule": idx, "path": rule.get("collection") or path,
                                   "message": rule.get("message", "数量不符合")})
            elif check == "refExists":
                refs = _flatten(values)
                ids = set(_target_ids(rule, data, context))
                missing = sorted(set(refs) - ids)
                if missing:
                    errors.append({"rule": idx, "path": path, "missing": missing,
                                   "message": rule.get("message", "引用不存在")})
            elif check == "relatedForbidden":
                items = _first(data, rule.get("items", "")) if rule.get("items") else values
                items = items if isinstance(items, list) else []
                targets = _values(data, rule.get("targetPath", "")) if rule.get("targetPath") else []
                targets = targets[0] if targets and isinstance(targets[0], list) else targets
                by_key = {str(x.get(rule.get("targetKey", "id"))): x for x in targets if isinstance(x, dict)}
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    key = str(item.get(rule.get("itemKey", "id")) or "")
                    related = by_key.get(key)
                    if related and related.get(rule.get("forbiddenField")) == rule.get("forbiddenValue"):
                        errors.append({"rule": idx, "path": rule.get("targetPath", ""), "message": rule.get("message", "关联约束冲突")})
            else:
                errors.append({"rule": idx, "message": "未知规则：%s" % check})
        return {"ok": not errors, "errors": errors}
