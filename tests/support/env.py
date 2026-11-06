"""测试环境：临时配置目录、接口配置构造器、演示库、不经 HTTP 的快捷调用。"""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from lowcode.core import Context
from lowcode.runtime import Runtime, build_runtime

ROOT = Path(__file__).resolve().parents[2]
CONF = ROOT / "conf"                 # 演示配置目录
DATA = ROOT / "data"                 # 演示库与建库脚本

SERVER_YAML = """
server: {timeout: 2, debug: true}
dataSources:
  - {name: main, type: sqlite, config: {path: ./t.db}}
"""


def write_files(root: Path, files: Dict[str, str]) -> None:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


def api(graph: str = None, **fields: str) -> str:
    """构造满足接口必填字段（name/method/desc/inputs/outputs）的 yaml，graph 为节点文本。

    fields 可覆盖任意元字段（值直接写入 yaml）。path 是必填的完整路径，默认与
    文件名 g_a_a.yaml 一致；用别的文件名时要显式传 path（如 path="/h/b/c"）。
    graph=None 时使用一个默认的 respBuilder 节点，传空串则接口不含 graph。
    """
    meta = {"name": "测试接口", "method": "GET", "path": "/g/a/a", "desc": "测试接口",
            "inputs": "[]", "outputs": "[]"}
    meta.update(fields)
    head = "".join(f"{k}: {v}\n" for k, v in meta.items())
    if graph is None:
        graph = "graph: [{name: respBuilder, config: {data: 1}}]"
    return head + (textwrap.dedent(graph).lstrip("\n") if graph else "")


def make_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            create table users (id integer primary key, name text not null, level integer not null);
            insert into users(name, level) values ('a', 1), ('b', 2), ('c', 3), ('d', 3), ('e', 5);
        """)


class TempConfCase(unittest.TestCase):
    """每个用例一个临时配置目录（自带 server.yaml 与 t.db），用完即删。"""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="lowcode_test_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        make_db(self.root / "t.db")

    def conf(self, files: Dict[str, str], server: Optional[str] = SERVER_YAML) -> Path:
        if server is not None:
            files = {"server.yaml": server, **files}
        write_files(self.root, files)
        return self.root

    def runtime(self, files: Dict[str, str], server: Optional[str] = SERVER_YAML) -> Runtime:
        rt = build_runtime(self.conf(files, server))
        self.addCleanup(rt.close)
        return rt


def call(rt: Runtime, key: str, raw: Optional[Dict[str, Any]] = None) -> Tuple[Any, Context]:
    """不经 HTTP，直接执行某个接口的计划。"""
    plan = next(p for p in rt.plans if p.key == key)
    ctx = Context(plan.inputs.parse(raw or {}), timeout=plan.timeout)
    return rt.executor.run(plan, ctx), ctx
