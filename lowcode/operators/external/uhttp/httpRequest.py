"""httpRequest：调用上游 HTTP 接口。手册与用例见 operator_md/external/uhttp/httpRequest.md。"""
from __future__ import annotations

from typing import Any, Dict

from ....datasources.http import http_call
from ....spec import Field
from ...base import Operator
from ...registry import register

_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")
_DEFAULT_TIMEOUT = 5


@register("httpRequest", category="external")
class HttpRequest(Operator):
    """调用 HTTP 接口，JSON 响应自动解析；非 2xx → 502，超时 → 504。"""

    spec = {
        "dataSource": Field(str, desc="HTTP 数据源（baseUrl / 公共 headers / 超时）；url 为绝对地址时可省略"),
        "url": Field(str, required=True, dynamic=True, desc="相对 baseUrl 的路径或绝对地址"),
        "method": Field(str, default="GET", choices=_METHODS),
        "query": Field(dict, default={}, dynamic=True, desc="查询参数；值为 null 的项不发送"),
        "headers": Field(dict, default={}, dynamic=True),
        "json": Field(object, dynamic=True, desc="JSON 请求体"),
        "timeout": Field((int, float), desc="超时（秒），缺省取数据源配置；不会超过接口剩余时间"),
    }

    def build(self) -> None:
        absolute = self.config["url"].startswith(("http://", "https://"))
        self.ds = None if absolute and not self.config["dataSource"] \
            else self.env.datasource(self.config["dataSource"], "http")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        own = args["timeout"] or (self.ds.timeout if self.ds else _DEFAULT_TIMEOUT)
        timeout = max(min(own, ctx.remaining()), 0.001)  # 只用接口剩余时间，避免整体超时后还在等上游
        kwargs = dict(query=args["query"], body=args["json"], headers=args["headers"], timeout=timeout)
        if self.ds is not None:
            return self.ds.request(args["method"], args["url"], **kwargs)
        return http_call(args["method"], args["url"], **kwargs)
