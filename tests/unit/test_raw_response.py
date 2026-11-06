"""RawResponse：任意算子返回原始 HTTP 时，Web 层绕过统一信封。"""
import unittest
from unittest.mock import patch

from lowcode import RawResponse, create_app

from ..support import TempConfCase, api

SERVER = "server: {timeout: 2}\ndataSources: []"


class RawResponseTest(TempConfCase):
    def test_view_returns_raw_response(self):
        app = create_app(self.conf(
            {"g_a_a.yaml": api("graph: [{name: respBuilder, config: {data: 1}}]")}, SERVER))
        self.addCleanup(app.extensions["lowcode"].close)
        rt = app.extensions["lowcode"]
        with patch.object(rt.executor, "run",
                          return_value=RawResponse("hello", 201, {"X-Test": "1"})):
            resp = app.test_client().get("/g/a/a")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data, b"hello")
        self.assertEqual(resp.headers["X-Test"], "1")

    def test_normal_output_still_uses_envelope(self):
        app = create_app(self.conf(
            {"g_a_a.yaml": api("graph: [{name: respBuilder, config: {data: {ok: true}}}]")}, SERVER))
        self.addCleanup(app.extensions["lowcode"].close)
        body = app.test_client().get("/g/a/a").get_json()
        self.assertEqual((body["code"], body["data"]), (0, {"ok": True}))
