"""库式入口 Lowcode：加载配置、WSGI 可调用、run 参数覆盖、生命周期。"""
import unittest
from unittest.mock import patch

from lowcode import Lowcode, create_server

from ..support import TempConfCase, api

SERVER = "server: {timeout: 2}\ndataSources: []"


class LowcodeServerTest(TempConfCase):
    def make(self):
        files = {"g_a_a.yaml": api("graph: [{name: respBuilder, config: {data: {ok: true}}}]")}
        srv = Lowcode(self.conf(files, SERVER))
        self.addCleanup(srv.close)
        return srv

    def test_app_and_wsgi_callable(self):
        srv = self.make()
        body = srv.app.test_client().get("/g/a/a").get_json()
        self.assertEqual(body["data"], {"ok": True})
        self.assertTrue(callable(srv))  # 可直接作为 WSGI app 交给 gunicorn
        self.assertEqual(srv.plans[0].url, "/g/a/a")

    def test_run_defaults_and_overrides(self):
        srv = self.make()
        with patch.object(srv.app, "run") as run:
            srv.run()
            kw = run.call_args.kwargs
            self.assertEqual((kw["host"], kw["port"]), (srv.server.host, srv.server.port))
            srv.run(host="0.0.0.0", port=9000, debug=True)
            kw = run.call_args.kwargs
            self.assertEqual((kw["host"], kw["port"], kw["debug"]), ("0.0.0.0", 9000, True))

    def test_create_server_and_context_manager(self):
        root = self.conf({"g_a_a.yaml": api("graph: [{name: respBuilder, config: {data: 1}}]")}, SERVER)
        srv = create_server(root)
        with srv as opened:
            self.assertIs(opened, srv)
        self.assertTrue(callable(srv))
