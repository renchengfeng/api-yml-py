"""文件算子的公共路径解析与摘要函数。"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from ....errors import BizError


def resolve(base_dir: str, rel: str, *, must_file: bool = False,
            must_exist: bool = False) -> Path:
    """把相对路径解析到 base_dir 内，拒绝绝对路径和目录穿越。"""
    base = Path(os.path.expandvars(str(base_dir or "."))).expanduser()
    if not base.is_absolute():
        base = Path.cwd() / base
    base = base.resolve()
    text = str(rel or "").strip()
    if not text:
        raise BizError("path 不能为空", 400)
    if Path(text).is_absolute():
        raise BizError("path 必须是相对路径", 400)
    target = (base / text).resolve()
    if target != base and base not in target.parents:
        raise BizError("path 越界，必须位于 baseDir 内", 403)
    if must_exist and not target.exists():
        raise BizError("文件不存在：%s" % text, 404)
    if must_file:
        if not target.exists():
            raise BizError("文件不存在：%s" % text, 404)
        if not target.is_file():
            raise BizError("不是文件：%s" % text, 400)
    return target


def digest(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
