"""算子注册表与执行器单测。

各内置算子自身的行为由用例驱动测试覆盖：operator_md/<分类>/<算子名>_input.yaml + tests/operators/。
"""
import time
import unittest

from lowcode import Field, Operator, register
from lowcode.errors import BizError, ConfigError, DeadlineError, ExecError

from ..support import TempConfCase, api, call


class RegistryTest(TempConfCase):
    def test_register_rules(self):
        class Good(Operator):
            pass

        with self.assertRaises(TypeError):
            register("notOp")(object)
        with self.assertRaises(ValueError):
            register("Bad-Name")(Good)
        with self.assertRaises(ValueError):
            register("sqlQuery")(Good)  # 重名
        with self.assertRaises(TypeError):
            register("badSpec")(type("BadSpec", (Operator,), {"spec": {"a": 1}}))
        with self.assertRaises(ValueError):
            register("badSpec2")(type("BadSpec2", (Operator,), {"spec": {"a": Field(required=True, default=1)}}))

    def test_build_failure_is_wrapped(self):
        @register("brokenBuild", category="test")
        class Broken(Operator):
            def build(self):
                raise KeyError("oops")

        with self.assertRaises(ConfigError) as cm:
            self.runtime({"g_a_a.yaml": api("graph: [{name: brokenBuild}]")})
        self.assertIn("g_a_a.yaml › graph[0]: operator brokenBuild build failed: KeyError", str(cm.exception))


class ExecutorTest(TempConfCase):
    PARALLEL = api("""
    graph:
      - {id: a, name: sleep, config: {seconds: 0.2, value: 1}}
      - {id: b, name: sleep, depends: [], config: {seconds: 0.2, value: 2}}
      - {name: respBuilder, depends: [a, b], config: {data: "{{ a + b }}"}}
    """)

    def timed(self, server: str):
        rt = self.runtime({"g_a_a.yaml": self.PARALLEL}, server)
        start = time.perf_counter()
        result, ctx = call(rt, "GET /g/a/a")
        return result, time.perf_counter() - start, ctx

    def test_parallel_vs_serial(self):
        result, cost, ctx = self.timed("server: {parallel: true}")
        self.assertEqual(result, 3)
        self.assertLess(cost, 0.35)
        self.assertEqual({t["node"] for t in ctx.trace}, {"a", "b", "respBuilder"})
        _, cost, _ = self.timed("server: {parallel: false}")
        self.assertGreaterEqual(cost, 0.4)

    def test_timeouts(self):
        with self.assertRaises(DeadlineError):  # 并行层：wait 超时
            self.timed("server: {timeout: 0.1}")
        chain = api("""
        timeout: 0.1
        graph:
          - {name: sleep, config: {seconds: 0.15}}
          - {name: respBuilder, config: {data: 1}}
        """, path="/g/a/b")
        rt = self.runtime({"g_a_b.yaml": chain})
        with self.assertRaises(DeadlineError):  # 串行：下一层开始前检查截止时间
            call(rt, "GET /g/a/b")

    def test_error_wrapping_and_fast_fail(self):
        api_text = api("""
        graph:
          - {id: x, name: boom}
          - {id: y, name: sleep, depends: [], config: {seconds: 0.5}}
          - {name: respBuilder, depends: [x, y], config: {data: 1}}
        """)
        rt = self.runtime({"g_a_a.yaml": api_text})
        start = time.perf_counter()
        with self.assertRaises(ExecError) as cm:
            call(rt, "GET /g/a/a")
        self.assertEqual(str(cm.exception), "[x] RuntimeError: kaboom")
        self.assertLess(time.perf_counter() - start, 0.3)  # 同层有节点失败立即返回，不等慢节点

        expectGuard = api("graph: [{id: g, name: expectGuard, config: {expect: false, msg: 业务提示}}]", path="/h/b/c")
        rt = self.runtime({"h_b_c.yaml": expectGuard})
        with self.assertRaises(BizError) as cm:
            call(rt, "GET /h/b/c")
        self.assertEqual(cm.exception.msg, "业务提示")  # 业务错误不加节点前缀

        missing = api("graph: [{id: r, name: respBuilder, config: {data: '{{ request.nope }}'}}]",
                      path="/h/b/b")
        rt = self.runtime({"h_b_b.yaml": missing})
        with self.assertRaises(ExecError) as cm:
            call(rt, "GET /h/b/b")
        self.assertIn("[r] template lookup failed", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
