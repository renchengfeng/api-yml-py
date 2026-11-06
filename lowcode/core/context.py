"""请求上下文（黑板）：一次请求内所有节点共享，请求结束即丢弃。

对应 datamore_lite 的 DataBus。节点输出按 id 存放，模板通过 {{ 节点id.字段 }} 读取。
并行层中多个线程会同时写输出、读作用域，所以这两处都加锁
（一边插入一边复制 dict 会触发 "dictionary changed size during iteration"）。
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional


class Context:
    def __init__(self, inputs: Dict[str, Any], request: Optional[Dict[str, Any]] = None,
                 timeout: float = 10, trace_id: str = ""):
        self.trace_id = trace_id or uuid.uuid4().hex[:16]
        self.inputs = inputs              # 已校验的入参
        self.request = request or {}      # method / path / headers / query / body / remoteAddr
        self.timeout = timeout
        self.deadline = time.monotonic() + timeout
        self.trace: List[Dict[str, Any]] = []
        self._outputs: Dict[str, Any] = {}
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- 节点输出

    def set_output(self, node_id: str, value: Any) -> None:
        with self._lock:
            self._outputs[node_id] = value

    def output(self, node_id: str) -> Any:
        with self._lock:
            return self._outputs[node_id]

    def scope(self) -> Dict[str, Any]:
        """模板求值的命名空间：上游输出 + inputs + request（后两者是保留名，不会被节点覆盖）。"""
        with self._lock:
            scope = dict(self._outputs)
        scope["inputs"] = self.inputs
        scope["request"] = self.request
        return scope

    # ---------------------------------------------------------------- 超时与追踪

    def remaining(self) -> float:
        """距截止时间还剩多少秒（可能为负）。"""
        return self.deadline - time.monotonic()

    def record(self, node_id: str, op: str, ms: float, error: str = "", desc: str = "") -> None:
        with self._lock:
            entry = {"node": node_id, "op": op, "ms": round(ms, 2), "error": error}
            if desc:
                entry["desc"] = desc  # 节点在做什么，请求日志里一眼可读
            self.trace.append(entry)
