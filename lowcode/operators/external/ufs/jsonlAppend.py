"""jsonlAppend：追加 JSON Lines。"""
from __future__ import annotations

import json

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import resolve


@register("jsonlAppend", category="external")
class JsonlAppend(Operator):
    """把一个对象或对象列表追加为 JSONL 行。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许写入的根目录"),
        "path": Field(str, required=True, dynamic=True, desc="相对 baseDir 的 JSONL 文件"),
        "items": Field(object, required=True, dynamic=True, desc="对象或对象列表"),
        "createDirs": Field(bool, default=True, desc="父目录不存在时创建"),
    }

    def execute(self, ctx, args):
        items = args["items"]
        if not isinstance(items, list):
            items = [items]
        target = resolve(args["baseDir"], args["path"])
        if target.exists() and target.is_dir():
            raise BizError("目标不是文件：%s" % args["path"], 400)
        if not target.parent.exists():
            if not args["createDirs"]:
                raise BizError("父目录不存在：%s" % target.parent, 400)
            target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            for item in items:
                fh.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
        return {"path": str(args["path"]), "count": len(items)}
