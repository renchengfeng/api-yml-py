"""文件日志：按天切分、请求日志落盘、同名 handler 不重复。"""
import logging
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from lowcode.web.logfile import DailyFileHandler

from lowcode import create_app
from lowcode.web.app import _setup_logging

from ..support import TempConfCase, api


class FileLogTest(TempConfCase):
    def setUp(self):
        super().setUp()
        self.dir = Path(tempfile.mkdtemp(prefix="lc_log_"))
        self.log_path = self.dir / "logs" / "app.log"
        self._disabled = logging.root.manager.disable
        logging.disable(logging.NOTSET)  # 测试公共工具全局静音日志，这里临时恢复
        self.addCleanup(self._clean)

    def _clean(self):
        logger = logging.getLogger("lowcode")
        for handler in list(logger.handlers):
            if isinstance(handler, DailyFileHandler):
                logger.removeHandler(handler)
                handler.close()
        logging.disable(self._disabled)
        shutil.rmtree(self.dir, ignore_errors=True)

    def _file_handlers(self):
        return [h for h in logging.getLogger("lowcode").handlers
                if isinstance(h, DailyFileHandler)]

    def test_setup_logging_is_idempotent(self):
        _setup_logging("INFO", str(self.log_path), 3, self.dir)
        _setup_logging("INFO", str(self.log_path), 3, self.dir)
        handlers = self._file_handlers()
        self.assertEqual(len(handlers), 1)  # 同名文件不重复添加
        self.assertEqual(handlers[0].backup, 3)
        self.assertEqual(handlers[0].stem, "app")
        self.assertEqual(handlers[0].path_for(date.today()).name,
                         f"app-{date.today():%Y-%m-%d}.log")

    def test_request_is_written_to_file(self):
        server = f"server: {{timeout: 2, logFile: '{self.log_path}', logBackup: 3}}\ndataSources: []"
        root = self.conf({"g_a_a.yaml": api("graph: [{name: respBuilder, config: {data: 1}}]")}, server)
        app = create_app(root)
        self.addCleanup(app.extensions["lowcode"].close)
        app.test_client().get("/g/a/a")

        written = self.log_path.parent / f"{self.log_path.stem}-{date.today():%Y-%m-%d}.log"
        self.assertTrue(written.exists())
        text = written.read_text(encoding="utf-8")
        self.assertIn("caller=app.py:", text)   # 文件名:行号，便于定位
        self.assertIn("event=request", text)
        self.assertIn("event=nodes", text)      # 算子明细单独一行
        self.assertIn("detail=respBuilder(respBuilder)", text)
        self.assertIn("traceId=", text)
        self.assertIn("path=/g/a/a", text)
