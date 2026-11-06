"""fsTransaction：带补偿的文件操作事务。"""
from __future__ import annotations

import base64
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import digest, resolve


_OPS = {"write", "writeBase64", "copy", "copyTree", "delete", "deleteTree"}


class _Txn:
    def __init__(self, base: Path):
        self.base = base
        self.root = base / ".fs-txn" / uuid.uuid4().hex
        self.root.mkdir(parents=True, exist_ok=True)
        self.records: List[Dict[str, Any]] = []

    def backup(self, target: Path) -> None:
        if target == self.base or target == self.base / ".fs-txn" or self.base / ".fs-txn" in target.parents:
            raise BizError("事务目标不能是 baseDir 或事务目录", 403)
        existed = target.exists()
        stored = self.root / str(len(self.records))
        if existed:
            if target.is_symlink():
                raise BizError("事务目标不允许符号链接：%s" % target, 403)
            if target.is_dir():
                shutil.copytree(target, stored)
            elif target.is_file():
                stored.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, stored)
        self.records.append({"target": target, "existed": existed, "stored": stored})

    def rollback(self) -> None:
        for rec in reversed(self.records):
            target = rec["target"]
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            elif target.exists():
                target.unlink(missing_ok=True)
            if rec["existed"] and rec["stored"].exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                if rec["stored"].is_dir():
                    shutil.copytree(rec["stored"], target)
                else:
                    shutil.copy2(rec["stored"], target)

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


@register("fsTransaction", category="external")
class FsTransaction(Operator):
    """按顺序执行文件操作；失败时按逆序恢复已有目标。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "operations": Field(list, required=True, dynamic=True, desc="文件操作列表"),
    }

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        operations = args["operations"]
        if not isinstance(operations, list):
            raise BizError("operations 必须是列表", 400)
        base = resolve(args["baseDir"], ".")
        txn = _Txn(base)
        try:
            for op in operations:
                if not isinstance(op, dict) or op.get("op") not in _OPS:
                    raise BizError("非法事务操作", 400)
                kind = op["op"]
                if kind in ("write", "writeBase64"):
                    target = resolve(args["baseDir"], str(op.get("path") or ""))
                    txn.backup(target)
                    if kind == "writeBase64":
                        raw = base64.b64decode(str(op.get("contentBase64") or ""), validate=True)
                    else:
                        raw = str(op.get("content") or "").encode(str(op.get("encoding") or "utf-8"))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    tmp = target.with_name(".%s.tmp-%s" % (target.name, uuid.uuid4().hex[:8]))
                    try:
                        tmp.write_bytes(raw)
                        os.replace(tmp, target)
                    finally:
                        if tmp.exists():
                            tmp.unlink(missing_ok=True)
                elif kind in ("copy", "copyTree"):
                    src = resolve(args["baseDir"], str(op.get("from") or ""))
                    dst = resolve(args["baseDir"], str(op.get("to") or ""))
                    if src.is_symlink() or dst.is_symlink():
                        raise BizError("事务不允许符号链接", 403)
                    if not src.exists():
                        raise BizError("源不存在：%s" % op.get("from"), 404)
                    txn.backup(dst)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if kind == "copyTree":
                        if not src.is_dir():
                            raise BizError("源不是目录：%s" % op.get("from"), 400)
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    elif src.is_file():
                        shutil.copy2(src, dst)
                    else:
                        raise BizError("源不是文件：%s" % op.get("from"), 400)
                else:
                    target = resolve(args["baseDir"], str(op.get("path") or ""))
                    txn.backup(target)
                    if kind == "deleteTree":
                        if target.exists():
                            if not target.is_dir():
                                raise BizError("目标不是目录：%s" % op.get("path"), 400)
                            shutil.rmtree(target)
                    else:
                        if target.exists():
                            if target.is_dir():
                                raise BizError("目标不是文件：%s" % op.get("path"), 400)
                            target.unlink()
        except Exception:
            txn.rollback()
            txn.cleanup()
            raise
        txn.cleanup()
        return {"committed": True, "operations": len(operations)}
