"""fileSwapTree：用一个目录替换另一个目录。"""
from __future__ import annotations

import os
import shutil
import uuid
from typing import Any, Dict

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import resolve


def _count_files(root):
    total = 0
    for path in root.rglob("*"):
        if path.is_symlink():
            raise BizError("目录不允许符号链接：%s" % path, 403)
        if path.is_file():
            total += 1
    return total


@register("fileSwapTree", category="external")
class FileSwapTree(Operator):
    """把 from 目录 rename 为 to；已有目标会先移到 backup 保留。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "from": Field(str, required=True, dynamic=True, desc="源目录，交换后会被移走"),
        "to": Field(str, required=True, dynamic=True, desc="目标目录"),
        "maxFiles": Field(int, default=5000, desc="最大文件数"),
    }

    def build(self) -> None:
        if self.config["maxFiles"] <= 0:
            raise self.config_error("maxFiles 必须大于 0", "maxFiles")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        src = resolve(args["baseDir"], args["from"])
        dst = resolve(args["baseDir"], args["to"])
        if src == dst or src in dst.parents or dst in src.parents:
            raise BizError("from / to 不能相同或互相包含", 400)
        if not src.is_dir():
            raise BizError("源目录不存在：%s" % args["from"], 404)
        if dst.exists() and not dst.is_dir():
            raise BizError("目标不是目录：%s" % args["to"], 400)
        if _count_files(src) > args["maxFiles"]:
            raise BizError("文件数超过上限 %d" % args["maxFiles"], 413)
        backup = None
        try:
            if dst.exists():
                backup = dst.with_name(".%s.backup-%s" % (dst.name, uuid.uuid4().hex[:8]))
                os.replace(dst, backup)
            os.replace(src, dst)
        except Exception:
            if backup is not None and backup.exists() and not dst.exists():
                os.replace(backup, dst)
            raise
        return {"from": str(args["from"]), "to": str(args["to"]),
                "backup": str(backup.name) if backup else ""}
