"""统一异常与错误码：LowcodeError 自带 code（业务码）与 status（HTTP 状态码）。"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, List, Optional


class LowcodeError(Exception):
    """框架异常基类。"""

    code = 500    # 响应体中的业务码
    status = 500  # HTTP 状态码

    def __init__(self, msg: str, code: Optional[int] = None, status: Optional[int] = None):
        super().__init__(msg)
        self.msg = msg
        self.node: Optional[str] = None  # 出错节点 id（由执行器填写）
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status

    def at_node(self, node_id: str) -> "LowcodeError":
        """给错误信息加上出错节点前缀，只加一次（嵌套捕获时不会重复）。"""
        if self.node is None:
            self.node = node_id
            self.msg = f"[{node_id}] {self.msg}"
            self.args = (self.msg,)
        return self

    def __str__(self) -> str:
        return self.msg


class ConfigError(LowcodeError):
    """配置错误（启动期）。可一次携带多条错误，便于一次性列全。"""

    def __init__(self, msg: str = "", where: str = "", errors: Optional[List[str]] = None):
        self.errors = errors or [f"{where}: {msg}" if where else msg]
        super().__init__("\n".join(self.errors))


class ParamError(LowcodeError):
    """请求参数不合法。"""

    code = status = 400


class BizError(LowcodeError):
    """业务校验失败。code 在 400~599 时同时作为 HTTP 状态码，否则 HTTP 200。"""

    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg, code=code, status=code if 400 <= code < 600 else 200)


class UpstreamError(LowcodeError):
    """上游（HTTP / 数据库 / 缓存）返回错误。"""

    code = status = 502


class DeadlineError(LowcodeError):
    """超过接口超时时间。"""

    code = status = 504


class ExecError(LowcodeError):
    """算子执行中的非预期异常（代码缺陷、数据异常、模板求值失败等）。"""

    code = status = 500


class ErrorCollector:
    """收集多处 ConfigError，最后一次性抛出（配合 with errors.collect(): 使用）。"""

    def __init__(self) -> None:
        self.errors: List[str] = []

    @contextmanager
    def collect(self) -> Iterator[None]:
        try:
            yield
        except ConfigError as e:
            self.errors.extend(e.errors)

    def raise_if_any(self) -> None:
        if self.errors:
            raise ConfigError(errors=self.errors)
