"""fileCopy：复制一个文件。"""
from __future__ import annotations

import shutil
from typing import Any, Dict

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import digest, resolve


@register("fileCopy", category="external")
class FileCopy(Operator):
    """复制一个文件，默认不覆盖已有目标。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "from": Field(str, required=True, dynamic=True, desc="源文件相对路径"),
        "to": Field(str, required=True, dynamic=True, desc="目标文件相对路径"),
        "overwrite": Field(bool, default=False, desc="目标存在时是否覆盖"),
    }

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        src = resolve(args["baseDir"], args["from"], must_file=True)
        dst = resolve(args["baseDir"], args["to"])
        if dst.exists() and not args["overwrite"]:
            raise BizError("目标已存在：%s" % args["to"], 409)
        if dst.is_dir():
            raise BizError("目标不是文件：%s" % args["to"], 400)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return {"from": str(args["from"]), "to": str(args["to"]), "bytes": dst.stat().st_size, "rev": digest(dst)}
