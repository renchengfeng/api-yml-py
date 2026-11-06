"""fileWrite：原子写入一个文本文件。"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import digest, resolve


@register("fileWrite", category="external")
class FileWrite(Operator):
    """原子写入一个文本文件，可选 expectedRev 乐观锁。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "path": Field(str, required=True, dynamic=True, desc="相对 baseDir 的文件路径"),
        "content": Field(str, required=True, dynamic=True, desc="写入内容"),
        "encoding": Field(str, default="utf-8", desc="文本编码"),
        "atomic": Field(bool, default=True, desc="临时文件 + rename 原子写入"),
        "expectedRev": Field(str, default="", dynamic=True, desc="非空时校验旧文件摘要"),
        "createDirs": Field(bool, default=True, desc="父目录不存在时创建"),
    }

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        target = resolve(args["baseDir"], args["path"])
        if target.exists() and target.is_dir():
            raise BizError("目标不是文件：%s" % args["path"], 400)
        expected = str(args["expectedRev"] or "").strip()
        if expected:
            if not target.exists():
                raise BizError("文件不存在，无法校验 rev：%s" % args["path"], 409)
            actual = digest(target)
            if actual != expected and not (len(expected) == 12 and actual.startswith(expected)):
                raise BizError("文件已被修改（rev 不匹配）：%s" % args["path"], 409)
        if not target.parent.exists():
            if not args["createDirs"]:
                raise BizError("父目录不存在：%s" % target.parent, 400)
            target.parent.mkdir(parents=True, exist_ok=True)
        raw = args["content"].encode(args["encoding"])
        if args["atomic"]:
            tmp = target.with_name(".%s.tmp-%s" % (target.name, uuid.uuid4().hex[:8]))
            try:
                tmp.write_bytes(raw)
                os.replace(tmp, target)
            finally:
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
        else:
            target.write_bytes(raw)
        return {"path": str(args["path"]), "bytes": len(raw), "rev": digest(target)}
