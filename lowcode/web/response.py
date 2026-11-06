"""响应信封：{code, msg, traceId, data}（字段名与 datamore_lite 的 DataMoreRsp 一致）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict

from flask import Response, jsonify
from flask.json.provider import DefaultJSONProvider

# debug 关闭时 5xx 只返回概括信息，详情写日志（避免把内部路径、上游地址暴露给调用方）
_GENERIC_MSG = {500: "服务内部错误", 502: "上游服务异常", 504: "处理超时"}


class JSONProvider(DefaultJSONProvider):
    """中文不转义、保持字段顺序；额外支持 bytes / set / tuple，日期用 ISO 格式。"""

    ensure_ascii = False
    sort_keys = False

    @staticmethod
    def default(o: Any) -> Any:
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, (bytes, bytearray)):
            return o.decode("utf-8", "replace")
        if isinstance(o, (set, frozenset, tuple)):
            return list(o)
        return DefaultJSONProvider.default(o)


@dataclass
class RawResponse:
    """算子返回的原始 HTTP 结果：Web 层不套 lowcode 信封，直接输出（文件 / 二进制 / 自定义状态码）。"""

    payload: Any
    status: int = 200
    headers: Dict[str, str] = field(default_factory=dict)


def envelope(code: int, msg: str, data: Any, trace_id: str, status: int = 200) -> Response:
    """响应体固定为 {code, msg, traceId, data}；节点耗时由 Web 层写入服务端日志。"""
    body: Dict[str, Any] = {"code": code, "msg": msg, "traceId": trace_id, "data": data}
    resp = jsonify(body)
    resp.status_code = status
    return resp


def public_msg(status: int, msg: str, trace_id: str, debug: bool) -> str:
    """对外展示的错误信息：debug 关闭时隐藏 5xx 细节。"""
    if debug or status < 500:
        return msg
    return f"{_GENERIC_MSG.get(status, '服务异常')}（traceId={trace_id}）"
