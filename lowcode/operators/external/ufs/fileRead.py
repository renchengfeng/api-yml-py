"""fileRead：读取一个文本文件。"""
from __future__ import annotations

from typing import Any, Dict

from ....errors import BizError, ExecError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import digest, resolve


@register("fileRead", category="external")
class FileRead(Operator):
    """读取一个文本文件，返回内容、大小和 rev。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "path": Field(str, required=True, dynamic=True, desc="相对 baseDir 的文件路径"),
        "encoding": Field(str, default="utf-8", desc="文本编码"),
        "maxBytes": Field(int, default=2 * 1024 * 1024, desc="允许读取的最大字节数"),
    }

    def build(self) -> None:
        if self.config["maxBytes"] <= 0:
            raise self.config_error("maxBytes 必须大于 0", "maxBytes")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        target = resolve(args["baseDir"], args["path"], must_file=True)
        size = target.stat().st_size
        if size > args["maxBytes"]:
            raise BizError("文件超过读取上限 %d 字节：%s" % (args["maxBytes"], args["path"]), 413)
        try:
            text = target.read_text(encoding=args["encoding"])
        except UnicodeDecodeError as exc:
            raise ExecError("文件编码不是 %s：%s" % (args["encoding"], args["path"])) from exc
        return {"path": str(args["path"]), "content": text, "bytes": size, "rev": digest(target)}
