"""fileImportTree：导入目录，支持冲突策略与备份。"""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import resolve


def _copy_tree(src: Path, dst: Path) -> int:
    files = 0
    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        if path.is_symlink():
            raise BizError("导入目录不允许符号链接：%s" % path, 403)
        rel = path.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        files += 1
    return files


@register("fileImportTree", category="external")
class FileImportTree(Operator):
    """把 from 目录导入 to；冲突可 error / overwrite / version。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "from": Field(str, required=True, dynamic=True, desc="源目录"),
        "to": Field(str, required=True, dynamic=True, desc="目标目录"),
        "conflict": Field(str, default="error", dynamic=True,
                            choices=("error", "overwrite", "version"),
                            desc="目标已存在时的策略"),
        "maxFiles": Field(int, default=5000, desc="最大文件数"),
    }

    def build(self) -> None:
        if self.config["maxFiles"] <= 0:
            raise self.config_error("maxFiles 必须大于 0", "maxFiles")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        src = resolve(args["baseDir"], args["from"])
        requested = resolve(args["baseDir"], args["to"])
        if src == requested or src in requested.parents or requested in src.parents:
            raise BizError("from / to 不能相同或互相包含", 400)
        if requested == resolve(args["baseDir"], "."):
            raise BizError("to 不能是 baseDir", 403)
        if not src.is_dir():
            raise BizError("源目录不存在：%s" % args["from"], 404)
        count = sum(1 for p in src.rglob("*") if p.is_file())
        if count > args["maxFiles"]:
            raise BizError("文件数超过上限 %d" % args["maxFiles"], 413)

        dst = requested
        versioned = False
        if dst.exists():
            if args["conflict"] == "error":
                raise BizError("目标已存在：%s" % args["to"], 409)
            if args["conflict"] == "version":
                base = dst
                index = 2
                while True:
                    candidate = base.with_name("%s-v%d" % (base.name, index))
                    if not candidate.exists():
                        dst = candidate
                        versioned = True
                        break
                    index += 1

        staging = dst.with_name(".%s.import-%s" % (dst.name, uuid.uuid4().hex[:8]))
        backup = None
        try:
            _copy_tree(src, staging)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                backup = dst.with_name(".%s.backup-%s" % (dst.name, uuid.uuid4().hex[:8]))
                os.replace(dst, backup)
            os.replace(staging, dst)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            if backup is not None and backup.exists() and not dst.exists():
                os.replace(backup, dst)
            raise
        return {"from": str(args["from"]), "to": dst.relative_to(resolve(args["baseDir"], ".")).as_posix(),
                "backup": str(backup.name) if backup else "", "versioned": versioned, "files": count}
