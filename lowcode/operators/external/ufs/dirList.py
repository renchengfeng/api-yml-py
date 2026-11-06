"""dirList：列出目录条目。"""
from __future__ import annotations

from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import resolve


@register("dirList", category="external")
class DirList(Operator):
    """列出目录下的直接子项，可按前缀过滤。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "subdir": Field(str, default="", dynamic=True, desc="相对 baseDir 的目录"),
        "prefix": Field(str, default="", dynamic=True, desc="只保留名称以此开头的条目"),
        "limit": Field(int, default=0, desc="最多返回条数，0 表示不限"),
    }

    def execute(self, ctx, args):
        root = resolve(args["baseDir"], args["subdir"] or ".")
        if not root.is_dir():
            return {"items": [], "count": 0}
        items = []
        for path in sorted(root.iterdir()):
            if args["prefix"] and not path.name.startswith(args["prefix"]):
                continue
            if args["limit"] and len(items) >= args["limit"]:
                break
            st = path.stat()
            items.append({"name": path.name,
                          "path": path.relative_to(root).as_posix(),
                          "type": "dir" if path.is_dir() else "file",
                          "size": st.st_size, "mtime": st.st_mtime})
        return {"items": items, "count": len(items)}
