"""zipExtract：安全解压一个 base64 zip。"""
from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import resolve


@register("zipExtract", category="external")
class ZipExtract(Operator):
    """把 base64 zip 安全解压到 baseDir 下的目标目录。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许写入的根目录"),
        "target": Field(str, required=True, dynamic=True, desc="相对 baseDir 的目标目录"),
        "zipBase64": Field(str, required=True, dynamic=True, desc="zip 文件的 base64"),
        "maxFiles": Field(int, default=2000, desc="最大文件数"),
        "maxBytes": Field(int, default=20 * 1024 * 1024, desc="最大解压总字节数"),
    }

    def build(self) -> None:
        if self.config["maxFiles"] <= 0 or self.config["maxBytes"] <= 0:
            raise self.config_error("maxFiles / maxBytes 必须大于 0")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            raw = base64.b64decode(str(args["zipBase64"]), validate=True)
        except Exception as exc:
            raise BizError("zipBase64 不是合法 base64", 400) from exc
        try:
            archive = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile as exc:
            raise BizError("不是合法的 zip 文件", 400) from exc

        infos = [i for i in archive.infolist() if not i.is_dir()]
        if len(infos) > args["maxFiles"]:
            raise BizError("zip 文件数超过上限 %d" % args["maxFiles"], 413)
        total = sum(int(i.file_size) for i in infos)
        if total > args["maxBytes"]:
            raise BizError("zip 解压后超过上限 %d 字节" % args["maxBytes"], 413)

        target = resolve(args["baseDir"], args["target"])
        target.mkdir(parents=True, exist_ok=True)
        written: List[str] = []
        for info in infos:
            member = PurePosixPath(str(info.filename).replace("\\", "/").lstrip("/"))
            if not member.parts or member.is_absolute() or ".." in member.parts:
                raise BizError("zip 路径非法：%s" % info.filename, 403)
            out = (target / Path(*member.parts)).resolve()
            if out != target and target not in out.parents:
                raise BizError("zip 路径越界：%s" % info.filename, 403)
            if (info.external_attr >> 16) & 0o120000 == 0o120000:
                continue  # 忽略符号链接
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(archive.read(info))
            written.append(member.as_posix())
        return {"target": str(args["target"]), "files": written, "count": len(written), "bytes": total}
