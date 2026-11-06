"""HTTP 数据源（标准库 urllib，零依赖）。

数据源提供 baseUrl / 公共 headers / 默认超时；具体请求参数由 httpRequest 算子给出。
http_call() 也可单独使用（url 为绝对地址、不需要数据源时）。
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from ..errors import ConfigError, DeadlineError, UpstreamError
from ..spec import Field, child
from . import DataSource, register_datasource


@register_datasource("http")
class HttpDataSource(DataSource):
    kind = "http"
    spec = {
        "baseUrl": Field(str, required=True, desc="如 https://api.example.com"),
        "timeout": Field((int, float), default=5, desc="默认超时（秒）"),
        "headers": Field(dict, default={}, desc="公共请求头"),
    }

    def check(self) -> None:
        if not self.config["baseUrl"].startswith(("http://", "https://")):
            raise ConfigError("baseUrl must start with http:// or https://", child(self.where, "baseUrl"))

    @property
    def timeout(self) -> float:
        return self.config["timeout"]

    def request(self, method: str, url: str, *, query: Optional[Dict[str, Any]] = None,
                body: Any = None, headers: Optional[Dict[str, Any]] = None,
                timeout: Optional[float] = None) -> Any:
        """相对 url 拼接 baseUrl；请求头 = 公共 headers + 本次 headers。"""
        if not url.startswith(("http://", "https://")):
            url = self.config["baseUrl"].rstrip("/") + "/" + url.lstrip("/")
        merged = {**self.config["headers"], **(headers or {})}
        return http_call(method, url, query=query, body=body, headers=merged,
                         timeout=timeout if timeout is not None else self.timeout)


def http_call(method: str, url: str, *, query: Optional[Dict[str, Any]] = None, body: Any = None,
              headers: Optional[Dict[str, Any]] = None, timeout: float = 5) -> Any:
    """发起一次 HTTP 请求。JSON 响应自动解析；非 2xx → UpstreamError(502)；超时 → DeadlineError(504)。"""
    if query:
        pairs = {k: v for k, v in query.items() if v is not None}  # None 表示"不传该参数"
        if pairs:
            url += ("&" if "?" in url else "?") + urlencode(pairs, doseq=True)
    hdrs = {str(k): str(v) for k, v in (headers or {}).items()}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310  url 来自配置
            return _decode(resp.read(), resp.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as e:
        snippet = e.read()[:200].decode("utf-8", "replace")
        raise UpstreamError(f"upstream returned HTTP {e.code}: {method} {url} → {snippet}") from None
    except (socket.timeout, TimeoutError):
        raise DeadlineError(f"上游超时（{timeout:.2f}s）：{method} {url}") from None
    except urllib.error.URLError as e:
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            raise DeadlineError(f"上游超时（{timeout:.2f}s）：{method} {url}") from None
        raise UpstreamError(f"upstream unreachable: {method} {url} → {e.reason}") from None


def _decode(raw: bytes, content_type: str) -> Any:
    text = raw.decode("utf-8", "replace")
    if "json" in content_type.lower():
        try:
            return json.loads(text)
        except ValueError:
            return text
    return text
