"""Web 层：把 Runtime 中的执行计划注册为 Flask 路由。

职责仅限 HTTP 相关：收集请求参数、traceId、统一响应、错误处理、访问与节点日志、元信息接口。
业务执行全部委托给 core.Executor，算子看不到 flask.request。
"""
from __future__ import annotations

import logging
import re
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from flask import Flask, Response, g, has_request_context, make_response, request
from werkzeug.exceptions import HTTPException

from ..core import ApiPlan, Context
from ..core.builder import response_shape
from ..errors import LowcodeError, ParamError
from ..operators import list_operators
from ..runtime import Runtime, build_runtime
from .logfile import DailyFileHandler
from .response import JSONProvider, RawResponse, envelope, public_msg

log = logging.getLogger("lowcode")
_TRACE_ID = re.compile(r"^[\w\-.]{1,64}$")  # 外部传入的 X-Request-Id 先校验格式，防日志注入
_HTTP_MSG = {404: "接口不存在", 405: "请求方法不支持", 413: "请求体过大", 415: "不支持的媒体类型"}


def create_app(conf_dir: Union[str, Path] = "conf") -> Flask:
    """应用工厂：装配 Runtime 并注册全部接口。配置有误时抛 ConfigError。"""
    rt = build_runtime(conf_dir)
    _setup_logging(rt.server.log_level, rt.server.log_file, rt.server.log_backup, rt.server.root)

    # static_folder=None：不注册 /static 路由，避免与配置里的接口路径冲突
    app = Flask(__name__, static_folder=None)
    app.json = JSONProvider(app)
    app.extensions["lowcode"] = rt

    for plan in rt.plans:
        app.add_url_rule(plan.rule, endpoint=plan.key, view_func=_make_view(plan, rt),
                         methods=[plan.method])
    if rt.server.meta:
        _register_meta(app, rt)
    _register_hooks(app, rt)
    _log(logging.INFO, "startup", name=rt.server.name, apis=len(rt.plans),
         datasources=len(rt.datasources.items()))
    return app


# ---------------------------------------------------------------- 接口视图

def _make_view(plan: ApiPlan, rt: Runtime) -> Callable[..., Any]:
    def view(**path_params: Any):
        inputs = plan.inputs.parse(_collect_params(path_params))
        ctx = Context(inputs, request=_request_info(), timeout=plan.timeout, trace_id=g.trace_id)
        g.ctx = ctx  # after_request 用它把节点耗时写入服务端日志
        data = rt.executor.run(plan, ctx)
        if isinstance(data, RawResponse):
            resp = make_response(data.payload, data.status)
            for key, value in data.headers.items():
                resp.headers[key] = value
            return resp
        return envelope(0, "ok", data, ctx.trace_id)

    view.__name__ = f"api_{plan.method}_{plan.url}"
    return view


def _json_body() -> Any:
    """解析 JSON 请求体（每个请求只解析一次）。Content-Type 是 JSON 但内容非法 → 400。"""
    if "json_body" not in g:
        body = None
        if request.is_json and request.get_data():
            body = request.get_json(silent=True)
            if body is None:
                raise ParamError("请求体不是合法的 JSON")
        g.json_body = body
    return g.json_body


def _collect_params(path_params: Dict[str, Any]) -> Dict[str, Any]:
    """合并参数来源，优先级：路径参数 > JSON body > form > query。同名多值保留为列表。"""
    params: Dict[str, Any] = {}
    for source in (request.args, request.form):
        for key in source:
            values = source.getlist(key)
            params[key] = values if len(values) > 1 else values[0]
    body = _json_body()
    if isinstance(body, dict):
        params.update(body)
    params.update(path_params)
    return params


def _request_info() -> Dict[str, Any]:
    """模板中的 {{ request.xxx }}。headers 的键统一小写；traceId 便于向上游透传链路。"""
    return {
        "method": request.method,
        "path": request.path,
        "headers": {k.lower(): v for k, v in request.headers.items()},
        "query": request.args.to_dict(),
        "body": _json_body(),
        "remoteAddr": request.remote_addr,
        "traceId": g.trace_id,
    }


# ---------------------------------------------------------------- 日志与钩子

def _log(level: int, event: str, **fields: Any) -> None:
    """一行一条日志：traceId=<id>|event=<事件>|k=v|...；按 traceId 可检索一次请求的所有日志。"""
    parts = [f"traceId={_current_trace_id()}", f"event={event}"]
    parts += [f"{key}={_one_line(value)}" for key, value in fields.items()]
    log.log(level, "|".join(parts), stacklevel=2)  # 行号指向 _log 的调用点


def _current_trace_id() -> str:
    return g.get("trace_id", "-") if has_request_context() else "-"


def _one_line(value: Any) -> str:
    """压成单行；竖线是字段分隔符，值内的竖线替换为分号。"""
    return " ".join(str(value).replace("|", ";").split())


def _node_timing(ctx: Optional[Context]) -> str:
    """只含节点 id 与耗时，供 event=request 汇总行使用。"""
    if ctx is None or not ctx.trace:
        return "-"
    return ",".join(f"{t['node']} {t['ms']}ms" for t in ctx.trace)


def _node_detail(ctx: Optional[Context]) -> str:
    """节点 id、算子、耗时、说明与错误，供 event=nodes 明细行使用；无节点时返回空串。"""
    if ctx is None or not ctx.trace:
        return ""
    parts = []
    for t in ctx.trace:
        part = f"{t['node']}({t['op']}) {t['ms']}ms"
        if t.get("desc"):
            part += " " + _one_line(t["desc"])
        if t["error"]:
            part += " error=" + _one_line(t["error"])
        parts.append(part)
    return ",".join(parts)


def _register_hooks(app: Flask, rt: Runtime) -> None:
    debug = rt.server.debug

    @app.before_request
    def _begin() -> None:
        rid = request.headers.get("X-Request-Id", "")
        g.trace_id = rid if _TRACE_ID.match(rid) else uuid.uuid4().hex[:16]
        g.start = time.perf_counter()

    @app.after_request
    def _end(resp):
        trace_id = g.get("trace_id", "-")
        resp.headers["X-Trace-Id"] = trace_id
        ms = (time.perf_counter() - g.get("start", time.perf_counter())) * 1000
        ctx = g.get("ctx")
        _log(logging.INFO, "request", method=request.method, path=request.path,
             status=resp.status_code, ms=f"{ms:.1f}", nodes=_node_timing(ctx))
        detail = _node_detail(ctx)
        if detail:
            _log(logging.INFO, "nodes", detail=detail)
        return resp

    @app.errorhandler(LowcodeError)
    def _on_lowcode_error(e: LowcodeError):
        trace_id = g.get("trace_id", "")
        if e.status >= 500:
            cause = f"{type(e.__cause__).__name__}: {e.__cause__}" if e.__cause__ else "-"
            _log(logging.ERROR, "error", code=e.code, status=e.status, msg=e.msg, cause=cause)
        return envelope(e.code, public_msg(e.status, e.msg, trace_id, debug), None, trace_id,
                        status=e.status)

    @app.errorhandler(HTTPException)
    def _on_http_error(e: HTTPException):
        resp = envelope(e.code, _HTTP_MSG.get(e.code, e.name), None, g.get("trace_id", ""), status=e.code)
        if e.code == 405:  # 保留 Allow 头，告诉调用方可用的方法
            resp.headers["Allow"] = e.get_response().headers.get("Allow", "")
        return resp

    @app.errorhandler(Exception)
    def _on_unexpected(e: Exception):
        trace_id = g.get("trace_id", "")
        _log(logging.ERROR, "exception", error=f"{type(e).__name__}: {e}",
             stack=_one_line(traceback.format_exc()))
        return envelope(500, public_msg(500, f"{type(e).__name__}: {e}", trace_id, debug), None,
                        trace_id, status=500)


# ---------------------------------------------------------------- 元信息接口

def _register_meta(app: Flask, rt: Runtime) -> None:
    @app.get("/_health")
    def _health():
        return envelope(0, "ok", {"status": "up", "apis": len(rt.plans)}, g.trace_id)

    @app.get("/_apis")
    def _apis():
        return envelope(0, "ok", [_describe_plan(p) for p in rt.plans], g.trace_id)

    @app.get("/_operators")
    def _operators():
        return envelope(0, "ok", [op.describe() for op in list_operators()], g.trace_id)


def _describe_plan(p: ApiPlan) -> Dict[str, Any]:
    doc: Dict[str, Any] = {
        "module": p.group.module, "group": p.group.group, "api": p.api.slug,
        "name": p.api.name, "method": p.method, "url": p.url,
        "desc": p.api.desc, "timeout": p.timeout, "file": p.api.where,
        "inputs": [{"name": d.name, "type": d.type, "required": d.required,
                    "default": d.default, "desc": d.desc} for d in p.inputs.defs],
        "outputs": [{"name": o.name, "type": o.type, "desc": o.desc} for o in p.api.outputs],
        "graph": [{"id": n.id, "operator": n.op.name, "depends": list(n.depends),
                   "desc": n.effective_desc} for n in p.nodes.values()],
        "levels": p.levels,
    }
    shape = response_shape(p)
    if shape is not None:
        doc["response"] = shape  # 响应结构骨架：动态表达式记为 …
    return doc


_LOG_FORMAT = ("caller=%(filename)s:%(lineno)d|time=%(asctime)s"
               "|level=%(levelname)s|logger=%(name)s|%(message)s")
_LOG_DATE = "%Y-%m-%d %H:%M:%S"


def _setup_logging(level: str, log_file: str = "", backup: int = 7,
                   root_dir: Optional[Path] = None) -> None:
    """控制台 + 可选文件日志（按天切分）。宿主程序已配置 root handler 时只补文件与级别。

    相对路径以配置根目录（server.yaml 所在目录）为基准；同名文件 handler 不会重复添加。
    """
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(format=_LOG_FORMAT, datefmt=_LOG_DATE)
        # werkzeug 的访问日志不带 traceId，与框架 event=request 重复；默认配置下只留框架日志
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
    log.setLevel(level)
    if not log_file:
        return
    path = Path(log_file)
    if not path.is_absolute() and root_dir is not None:
        path = Path(root_dir) / path
    path = path.resolve()
    target = (path.parent, path.stem)
    for handler in log.handlers:
        if isinstance(handler, DailyFileHandler) and (handler.directory, handler.stem) == target:
            return
    file_handler = DailyFileHandler(path.parent, path.stem, backup=backup)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE))
    log.addHandler(file_handler)
