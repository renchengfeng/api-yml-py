"""fileStat：读取路径元信息。"""
from __future__ import annotations

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import digest, resolve


@register("fileStat", category="external")
class FileStat(Operator):
    """返回路径类型、大小、修改时间与摘要。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "path": Field(str, required=True, dynamic=True, desc="相对路径"),
        "missingOk": Field(bool, default=False, desc="不存在时返回 exists=false"),
    }

    def execute(self, ctx, args):
        target = resolve(args["baseDir"], args["path"])
        if not target.exists():
            if args["missingOk"]:
                return {"exists": False, "path": str(args["path"])}
            raise BizError("路径不存在：%s" % args["path"], 404)
        st = target.stat()
        return {"exists": True, "path": str(args["path"]),
                "type": "dir" if target.is_dir() else "file",
                "size": st.st_size, "mtime": st.st_mtime,
                "rev": digest(target) if target.is_file() else ""}
