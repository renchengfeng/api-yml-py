"""fileReadMany：批量读取一个目录下的文件。"""
from __future__ import annotations

import fnmatch
import json
from typing import Any, Dict, List

import yaml

from ....errors import BizError
from ....spec import Field
from ...base import Operator
from ...registry import register
from ._path import digest, resolve


@register("fileReadMany", category="external")
class FileReadMany(Operator):
    """批量读取目录中的文件，并按 text / yaml / json / markdown 解析。"""

    spec = {
        "baseDir": Field(str, required=True, desc="允许访问的根目录"),
        "subdir": Field(str, default="", dynamic=True, desc="相对 baseDir 的子目录"),
        "suffix": Field(str, default=".yaml", desc="文件后缀，空字符串表示全部"),
        "recursive": Field(bool, default=False, desc="是否递归子目录"),
        "format": Field(str, default="text", choices=("text", "yaml", "json", "markdown"),
                        desc="读取后的解析格式"),
        "limit": Field(int, default=0, desc="最多读取条数，0 表示不限"),
        "skipInvalid": Field(bool, default=False, desc="解析失败时跳过该文件"),
        "exclude": Field(list, default=[], desc="跳过匹配这些 glob 的相对路径"),
    }

    def build(self) -> None:
        if self.config["limit"] < 0:
            raise self.config_error("limit 不能小于 0", "limit")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        base = resolve(args["baseDir"], args["subdir"] or ".")
        if not base.exists():
            return {"items": [], "count": 0}
        if not base.is_dir():
            raise BizError("subdir 不是目录：%s" % args["subdir"], 400)
        pattern = "*" if not args["suffix"] else "*" + args["suffix"]
        paths = base.rglob(pattern) if args["recursive"] else base.glob(pattern)
        items: List[Dict[str, Any]] = []
        for path in sorted(p for p in paths if p.is_file()):
            if args["limit"] and len(items) >= args["limit"]:
                break
            rel = path.relative_to(base).as_posix()
            if args["exclude"] and any(fnmatch.fnmatch(rel, pat) for pat in args["exclude"]):
                continue
            resolved = path.resolve()
            if resolved != base and base not in resolved.parents:
                if args["skipInvalid"]:
                    continue
                raise BizError("文件越界：%s" % path, 403)
            try:
                raw = path.read_text(encoding="utf-8")
                data = self._parse(raw, args["format"])
            except (UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
                if args["skipInvalid"]:
                    continue
                raise BizError("解析文件失败：%s：%s" % (path.name, exc), 400) from exc
            items.append({
                "path": rel,
                "data": data,
                "bytes": path.stat().st_size,
                "rev": digest(path),
            })
        return {"items": items, "count": len(items)}

    @staticmethod
    def _parse(raw: str, fmt: str) -> Any:
        if fmt == "yaml":
            return yaml.safe_load(raw)
        if fmt == "json":
            return json.loads(raw)
        if fmt == "markdown" and raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) < 3:
                raise ValueError("frontmatter 未闭合")
            return {"meta": yaml.safe_load(parts[1]) or {}, "body": parts[2].lstrip("\r\n")}
        return raw
