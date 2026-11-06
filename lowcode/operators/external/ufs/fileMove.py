"""fileMove：移动一个文件。"""
from __future__ import annotations

import os
from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import resolve


@register("fileMove", category="external")
class FileMove(Operator):
    """移动一个文件；默认不覆盖目标。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "from": Field(str, required=True, dynamic=True, desc="源文件"),
        "to": Field(str, required=True, dynamic=True, desc="目标文件"),
        "overwrite": Field(bool, default=False, desc="目标存在时是否覆盖"),
    }

    def execute(self, ctx, args):
        src = resolve(args["baseDir"], args["from"])
        dst = resolve(args["baseDir"], args["to"])
        if not src.is_file() or src.is_symlink():
            raise BizError("源文件不存在或不是普通文件：%s" % args["from"], 404)
        if dst.exists() and not args["overwrite"]:
            raise BizError("目标已存在：%s" % args["to"], 409)
        if dst.is_dir():
            raise BizError("目标不是文件：%s" % args["to"], 400)
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, dst)
        return {"from": str(args["from"]), "to": str(args["to"])}
