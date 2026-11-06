"""fileCopyTree：递归复制目录。"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import resolve


@register("fileCopyTree", category="external")
class FileCopyTree(Operator):
    """递归复制一个目录，限制文件数并拒绝符号链接逃逸。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "from": Field(str, required=True, dynamic=True, desc="源目录相对路径"),
        "to": Field(str, required=True, dynamic=True, desc="目标目录相对路径"),
        "overwrite": Field(bool, default=False, desc="目标已存在时是否覆盖"),
        "maxFiles": Field(int, default=5000, desc="最大复制文件数"),
    }

    def build(self) -> None:
        if self.config["maxFiles"] <= 0:
            raise self.config_error("maxFiles 必须大于 0", "maxFiles")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        src = resolve(args["baseDir"], args["from"])
        dst = resolve(args["baseDir"], args["to"])
        if not src.is_dir():
            raise BizError("源目录不存在：%s" % args["from"], 404)
        if dst.exists():
            if not args["overwrite"]:
                raise BizError("目标已存在：%s" % args["to"], 409)
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        dst.mkdir(parents=True, exist_ok=True)

        files = []
        total = 0
        for path in sorted(p for p in src.rglob("*") if p.is_file()):
            resolved = path.resolve()
            if resolved != src and src not in resolved.parents:
                raise BizError("源目录包含越界文件：%s" % path, 403)
            if path.is_symlink():
                raise BizError("源目录不允许符号链接：%s" % path, 403)
            if len(files) >= args["maxFiles"]:
                raise BizError("文件数超过上限 %d" % args["maxFiles"], 413)
            rel = path.relative_to(src)
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, out)
            files.append(rel.as_posix())
            total += path.stat().st_size
        return {"from": str(args["from"]), "to": str(args["to"]), "files": files,
                "count": len(files), "bytes": total}
