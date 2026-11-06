"""fileWriteMany：批量写文本 / base64 文件。"""
from __future__ import annotations

import base64
import os
import uuid
from typing import Any, Dict, List

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import digest, resolve


@register("fileWriteMany", category="external")
class FileWriteMany(Operator):
    """按顺序批量写文件；单文件失败会留下已完成的前缀。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许写入的根目录"),
        "files": Field(list, required=True, dynamic=True, desc="[{path, content|contentBase64, encoding?}]"),
        "atomic": Field(bool, default=True, desc="单文件临时文件 + rename"),
        "createDirs": Field(bool, default=True, desc="父目录不存在时创建"),
    }

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        files = args["files"]
        if not isinstance(files, list):
            raise BizError("files 必须是列表", 400)
        written: List[Dict[str, Any]] = []
        total = 0
        for item in files:
            if not isinstance(item, dict) or not item.get("path"):
                raise BizError("files 每项必须是 {path, content}", 400)
            target = resolve(args["baseDir"], str(item["path"]))
            if target.exists() and target.is_dir():
                raise BizError("目标不是文件：%s" % item["path"], 400)
            if item.get("contentBase64") is not None:
                try:
                    raw = base64.b64decode(str(item["contentBase64"]), validate=True)
                except Exception as exc:
                    raise BizError("contentBase64 不是合法 base64", 400) from exc
            else:
                raw = str(item.get("content") or "").encode(str(item.get("encoding") or "utf-8"))
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
            total += len(raw)
            written.append({"path": str(item["path"]), "bytes": len(raw), "rev": digest(target)})
        return {"files": written, "count": len(written), "bytes": total}
