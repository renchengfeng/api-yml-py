"""fileDeleteTree：递归删除目录。"""
from __future__ import annotations

import shutil

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import resolve


@register("fileDeleteTree", category="external")
class FileDeleteTree(Operator):
    """删除目录树；拒绝删除 baseDir 本身。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "path": Field(str, required=True, dynamic=True, desc="目录相对路径"),
        "missingOk": Field(bool, default=False, desc="目录不存在时是否成功"),
    }

    def execute(self, ctx, args):
        target = resolve(args["baseDir"], args["path"])
        if target == resolve(args["baseDir"], "."):
            raise BizError("不能删除 baseDir", 403)
        if not target.exists():
            if args["missingOk"]:
                return {"path": str(args["path"]), "deleted": False}
            raise BizError("目录不存在：%s" % args["path"], 404)
        if not target.is_dir():
            raise BizError("不是目录：%s" % args["path"], 400)
        if target.is_symlink():
            raise BizError("不允许删除符号链接", 403)
        shutil.rmtree(target)
        return {"path": str(args["path"]), "deleted": True}
