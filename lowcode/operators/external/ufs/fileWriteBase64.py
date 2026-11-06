"""fileWriteBase64：把 base64 内容原子写入文件。"""
from __future__ import annotations

import base64
import os
import uuid
from typing import Any, Dict

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import digest, resolve


@register("fileWriteBase64", category="external")
class FileWriteBase64(Operator):
    """解码 base64 并原子写入文件，适合二进制上传。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许写入的根目录"),
        "path": Field(str, required=True, dynamic=True, desc="相对 baseDir 的文件路径"),
        "contentBase64": Field(str, required=True, dynamic=True, desc="base64 内容"),
        "atomic": Field(bool, default=True, desc="临时文件 + rename"),
        "createDirs": Field(bool, default=True, desc="父目录不存在时创建"),
    }

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            raw = base64.b64decode(str(args["contentBase64"]), validate=True)
        except Exception as exc:
            raise BizError("contentBase64 不是合法 base64", 400) from exc
        target = resolve(args["baseDir"], args["path"])
        if target.exists() and target.is_dir():
            raise BizError("目标不是文件：%s" % args["path"], 400)
        if not target.parent.exists():
            if not args["createDirs"]:
                raise BizError("父目录不存在：%s" % target.parent, 400)
            target.parent.mkdir(parents=True, exist_ok=True)
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
