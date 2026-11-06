"""fileExists：判断路径是否存在。"""
from __future__ import annotations

from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import resolve


@register("fileExists", category="external")
class FileExists(Operator):
    """判断文件/目录是否存在，不抛 404。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "path": Field(str, required=True, dynamic=True, desc="相对路径"),
    }

    def execute(self, ctx, args):
        target = resolve(args["baseDir"], args["path"])
        kind = "dir" if target.is_dir() else "file" if target.is_file() else ""
        return {"exists": target.exists(), "type": kind, "path": str(args["path"])}
