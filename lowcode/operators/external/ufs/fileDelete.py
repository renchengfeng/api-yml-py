"""fileDelete：删除一个文件。"""
from __future__ import annotations

from typing import Any, Dict

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import resolve


@register("fileDelete", category="external")
class FileDelete(Operator):
    """删除一个文件；默认文件不存在时报 404。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "path": Field(str, required=True, dynamic=True, desc="相对 baseDir 的文件路径"),
        "missingOk": Field(bool, default=False, desc="文件不存在时是否视为成功"),
    }

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        target = resolve(args["baseDir"], args["path"])
        if not target.exists():
            if args["missingOk"]:
                return {"path": str(args["path"]), "deleted": False}
            raise BizError("文件不存在：%s" % args["path"], 404)
        if target.is_dir():
            raise BizError("拒绝删除目录：%s" % args["path"], 400)
        target.unlink()
        return {"path": str(args["path"]), "deleted": True}
