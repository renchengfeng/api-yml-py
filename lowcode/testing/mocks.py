"""声明式数据源 Mock：用例写 mocks，框架为每个用例构造一组独立数据源，用完即释放。

    mocks:
      sqlite: {name: main, setup: "create table ...; insert ..."}   # 真实 SqliteDataSource + 临时库
      http:   {routes: {GET /ok: {json: {a: 1}}, POST /echo: {echo: true}}}  # 真实 HttpDataSource + 本地服务
      redis:  {store: {k: v, h: {f1: v1}}}                          # 内存 KV，避免依赖 redis-py

sqlite 与 http 测到"算子 + 数据源"的完整路径；redis 只覆盖算子逻辑。各类型的字段见 *_SPEC。
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import time
from contextlib import ExitStack, closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from ..datasources import DataSource, DataSourceManager, create_datasource
from ..datasources.http import HttpDataSource
from ..datasources.sqlite import SqliteDataSource
from ..errors import ConfigError
from ..spec import Field, child, suggest, validate

SQLITE_SPEC = {
    "name": Field(str, default="sqlite"),
    "setup": Field(str, required=True, desc="建表与造数 SQL"),
    "readonly": Field(bool, default=False),
}
HTTP_SPEC = {
    "name": Field(str, default="http"),
    "routes": Field(dict, required=True, desc="'METHOD /path' → 响应"),
    "timeout": Field((int, float), default=2),
    "headers": Field(dict, default={}),
}
ROUTE_SPEC = {
    "status": Field(int, default=200),
    "json": Field(object, desc="JSON 响应体"),
    "text": Field(str, desc="文本响应体"),
    "delay": Field((int, float), default=0, desc="响应前等待（秒），用于测超时"),
    "echo": Field(bool, default=False, desc="回显收到的请求"),
}
REDIS_SPEC = {
    "name": Field(str, default="redis"),
    "store": Field(dict, default={}, desc="键 → 字符串（get）或对象（hgetall）"),
}


class MockRedis(DataSource):
    """内存 KV。不注册到数据源类型表，只在测试中直接实例化。"""

    type = "mockRedis"
    kind = "kv"
    spec = {"store": Field(dict, default={})}

    def get(self, key: str) -> Optional[str]:
        v = self.config["store"].get(key)
        return v if isinstance(v, str) else None

    def hgetall(self, key: str) -> Dict[str, str]:
        v = self.config["store"].get(key)
        return dict(v) if isinstance(v, dict) else {}


def build_mocks(mocks: Dict[str, Any], stack: ExitStack, where: str) -> DataSourceManager:
    """按用例的 mocks 构造数据源；所有资源（临时库、HTTP 服务）登记到 stack，用例结束时释放。"""
    builders: Dict[str, Callable[[Any, ExitStack, str], DataSource]] = {
        "sqlite": _sqlite, "http": _http, "redis": _redis}
    items: List[DataSource] = []
    for kind, conf in mocks.items():
        at = child(where, kind)
        if kind not in builders:
            raise ConfigError(f"unknown mock type {kind!r}{suggest(str(kind), list(builders))}", at)
        items.append(builders[kind](conf, stack, at))
    return DataSourceManager(items)


def _sqlite(conf: Any, stack: ExitStack, where: str) -> DataSource:
    c = validate(conf, SQLITE_SPEC, where)
    tmp = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="lowcode_mock_")))
    try:
        with closing(sqlite3.connect(tmp / "mock.db")) as conn, conn:
            conn.executescript(c["setup"])
    except sqlite3.Error as e:
        raise ConfigError(f"setup SQL failed: {e}", child(where, "setup")) from None
    return create_datasource(SqliteDataSource, c["name"], {"path": "mock.db", "readonly": c["readonly"]},
                             tmp, where)


def _redis(conf: Any, stack: ExitStack, where: str) -> DataSource:
    c = validate(conf, REDIS_SPEC, where)
    return create_datasource(MockRedis, c["name"], {"store": c["store"]}, Path("."), where)


def _http(conf: Any, stack: ExitStack, where: str) -> DataSource:
    c = validate(conf, HTTP_SPEC, where)
    routes: Dict[str, Dict[str, Any]] = {}
    for key, resp in c["routes"].items():
        at = child(child(where, "routes"), key)
        parts = str(key).split(" ", 1)
        if len(parts) != 2 or not parts[1].startswith("/"):
            raise ConfigError("route key must be 'METHOD /path', e.g. 'GET /ok'", at)
        r = validate(resp, ROUTE_SPEC, at)
        bodies = [k for k in ("json", "text") if r[k] is not None] + (["echo"] if r["echo"] else [])
        if len(bodies) > 1:
            raise ConfigError(f"only one of {' / '.join(bodies)} may be set", at)
        routes[f"{parts[0].upper()} {parts[1]}"] = r

    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(routes))
    server.daemon_threads = True
    # poll_interval 默认 0.5s：shutdown() 要等它轮询到才返回，每个用例白等半秒，这里调小
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
    stack.callback(server.server_close)
    stack.callback(server.shutdown)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    return create_datasource(HttpDataSource, c["name"],
                             {"baseUrl": base, "timeout": c["timeout"], "headers": c["headers"]},
                             Path("."), where)


def _make_handler(routes: Dict[str, Dict[str, Any]]) -> type:
    class Handler(BaseHTTPRequestHandler):
        def _handle(self) -> None:
            u = urlparse(self.path)
            route = routes.get(f"{self.command} {u.path}")
            if route is None:
                return self._send(404, b"no mock route", "text/plain")
            if route["delay"]:
                time.sleep(route["delay"])
            if route["echo"]:
                return self._send(route["status"], _json(self._echo(u)), "application/json")
            if route["text"] is not None:
                return self._send(route["status"], route["text"].encode("utf-8"), "text/plain")
            return self._send(route["status"], _json(route["json"]), "application/json")

        def _echo(self, u) -> Dict[str, Any]:
            """回显请求。headers 只保留 X- 开头的自定义头（Host / User-Agent 等随环境变化，不宜断言）。"""
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            query = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(u.query).items()}
            return {
                "method": self.command, "path": u.path, "query": query,
                "headers": {k.lower(): v for k, v in self.headers.items() if k.lower().startswith("x-")},
                "contentType": self.headers.get("Content-Type"),
                "json": json.loads(raw) if raw else None,
            }

        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):  # 客户端已超时断开
                pass

        do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _handle

        def log_message(self, *args: Any) -> None:
            pass

    return Handler


def _json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")
