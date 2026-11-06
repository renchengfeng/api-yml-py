"""Web 层单测：响应信封、debug 开关、日志格式、元信息开关（用最小临时配置）。"""
import logging
import unittest
from contextlib import contextmanager

from lowcode import create_app

from ..support import TempConfCase, api


class WebBehaviorTest(TempConfCase):
    BOOM = api("graph: [{name: boom}]")

    def client(self, server: str, files=None):
        app = create_app(self.conf(files or {"g_a_a.yaml": self.BOOM}, server))
        self.addCleanup(app.extensions["lowcode"].close)
        return app.test_client()

    @contextmanager
    def capture_logs(self):
        disabled = logging.root.manager.disable
        logging.disable(logging.NOTSET)  # 测试公共工具全局静音日志，这里临时恢复
        try:
            with self.assertLogs("lowcode", level="INFO") as cm:
                yield cm
        finally:
            logging.disable(disabled)

    def test_5xx_detail_hidden_unless_debug(self):
        body = self.client("server: {debug: false}").get("/g/a/a").get_json()
        self.assertTrue(body["msg"].startswith("服务内部错误（traceId="))
        self.assertNotIn("trace", body)  # debug 关闭：无 trace
        body = self.client("server: {debug: true}").get("/g/a/a").get_json()
        self.assertEqual(body["msg"], "[boom] RuntimeError: kaboom")
        self.assertNotIn("trace", body)  # debug 开启也只影响错误信息，响应永远不带 trace

    def test_node_trace_written_to_server_log(self):
        with self.capture_logs() as cm:
            body = self.client("server: {debug: false}").get("/g/a/a").get_json()
        lines = "\n".join(cm.output)
        self.assertNotIn("trace", body)
        self.assertIn("event=error|", lines)
        self.assertIn("event=request|", lines)
        self.assertIn("nodes=boom(boom)", lines)
        self.assertIn("error=[boom] RuntimeError: kaboom", lines)

    def test_log_lines_are_single_kv_strings_sharing_trace_id(self):
        with self.capture_logs() as cm:
            c = self.client("server: {debug: false}")
            c.get("/g/a/a", headers={"X-Request-Id": "req-abc-123"})
            c.get("/_health", headers={"X-Request-Id": "req-health"})
        messages = [line.split(":", 2)[2] for line in cm.output]
        for message in messages:
            self.assertNotIn("\n", message)
            for field in message.split("|"):
                self.assertIn("=", field, message)
            self.assertTrue(message.startswith("traceId="))
            self.assertIn("|event=", message)
        same = [m for m in messages if "traceId=req-abc-123" in m]
        self.assertEqual(len(same), 2)  # 一次请求的错误日志与访问日志
        self.assertEqual({m.split("event=")[1].split("|")[0] for m in same}, {"error", "request"})

    def test_meta_switch_and_repeated_query(self):
        api_text = api("graph: [{name: respBuilder, config: {data: '{{ inputs.ids }}'}}]",
                       inputs="[{name: ids, type: list, desc: id 列表}]")
        c = self.client("server: {meta: false}", {"g_a_a.yaml": api_text})

        self.assertEqual(c.get("/_apis").status_code, 404)
        self.assertEqual(c.get("/g/a/a?ids=1&ids=2").get_json()["data"], ["1", "2"])
        self.assertEqual(c.get("/g/a/a?ids=3,4").get_json()["data"], ["3", "4"])
