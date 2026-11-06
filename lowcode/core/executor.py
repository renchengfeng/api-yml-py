"""执行器：按 ApiPlan 的分层逐层执行节点（对应 datamore_lite 的 Executor + AOP）。

- 层与层串行；同层多个节点且开启 parallel 时并发；每层开始前检查截止时间。
- 单个节点的执行包装（run_node）：渲染 args → execute → 写黑板 → 记 trace → 错误加节点前缀。
  算子测试框架（lowcode.testing）直接调用 run_node，与线上走同一条路径。
"""
from __future__ import annotations

import time
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from typing import Any, List, Optional

from ..errors import BizError, DeadlineError, ExecError, LowcodeError
from .builder import ApiPlan, PlanNode
from .context import Context


class Executor:
    def __init__(self, parallel: bool = True, workers: int = 8):
        # 线程池全局共享：请求线程只负责等待，不会占用池内线程，所以不会互相等待而死锁
        self._pool: Optional[ThreadPoolExecutor] = (
            ThreadPoolExecutor(max_workers=workers, thread_name_prefix="lowcode")
            if parallel and workers > 1 else None)

    def run(self, plan: ApiPlan, ctx: Context) -> Any:
        """执行整个计划，返回结果节点的输出。"""
        for level in plan.levels:
            if ctx.remaining() <= 0:
                raise DeadlineError(f"api timed out after ({plan.timeout}s)")
            if self._pool is not None and len(level) > 1:
                self._run_parallel(plan, level, ctx)
            else:
                for node_id in level:
                    self.run_node(plan.nodes[node_id], ctx)
        return ctx.output(plan.result)

    def _run_parallel(self, plan: ApiPlan, level: List[str], ctx: Context) -> None:
        """同层并发。任一节点失败立即返回（快速失败，不等慢节点）；
        若返回时已有多个节点失败，按定义顺序取第一个。"""
        futures = [self._pool.submit(self.run_node, plan.nodes[nid], ctx) for nid in level]
        done, pending = wait(futures, timeout=max(ctx.remaining(), 0), return_when=FIRST_EXCEPTION)
        for f in futures:
            if f in done and f.exception() is not None:
                raise f.exception()
        if pending:
            unfinished = ", ".join(nid for nid, f in zip(level, futures) if f in pending)
            raise DeadlineError(f"api timed out after ({plan.timeout}s), unfinished nodes: {unfinished}")

    @staticmethod
    def run_node(node: PlanNode, ctx: Context) -> None:
        """执行单个节点并把输出写入黑板（所有节点执行的唯一入口）。"""
        start = time.perf_counter()
        error = ""
        try:
            args = node.resolve_args(ctx.scope())
            ctx.set_output(node.id, node.op.execute(ctx, args))
        except BizError as e:          # 业务错误是给调用方看的，原样透出
            error = e.msg
            raise
        except LowcodeError as e:      # 框架错误：加上节点前缀便于定位
            error = e.at_node(node.id).msg
            raise
        except Exception as e:         # noqa: BLE001  非预期异常统一包装为 500
            err = ExecError(f"{type(e).__name__}: {e}").at_node(node.id)
            error = err.msg
            raise err from e
        finally:
            ctx.record(node.id, node.op.name, (time.perf_counter() - start) * 1000, error,
                       desc=node.effective_desc)

    def shutdown(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False)
