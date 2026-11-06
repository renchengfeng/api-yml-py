"""hashTree：计算目录树摘要与文件统计。"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import resolve


@register("hashTree", category="external")
class HashTree(Operator):
    """返回目录树的 sha1、文件数和字节数；拒绝符号链接。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "path": Field(str, required=True, dynamic=True, desc="目录相对路径"),
    }

    def execute(self, ctx, args):
        root = resolve(args["baseDir"], args["path"])
        if not root.is_dir():
            raise BizError("目录不存在：%s" % args["path"], 404)
        digest = hashlib.sha1()
        files = 0
        total = 0
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            if path.is_symlink():
                raise BizError("目录不允许符号链接：%s" % path, 403)
            rel = path.relative_to(root).as_posix()
            digest.update(rel.encode("utf-8"))
            data = path.read_bytes()
            digest.update(data)
            files += 1
            total += len(data)
        return {"path": str(args["path"]), "hash": digest.hexdigest(),
                "files": files, "bytes": total, "mtime": root.stat().st_mtime}
