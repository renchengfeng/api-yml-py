"""测试共享工具。导入 ops 即注册测试专用算子。"""
import logging

logging.disable(logging.CRITICAL)  # 测试中屏蔽访问日志与预期内的错误日志

from .env import CONF, DATA, ROOT, SERVER_YAML, TempConfCase, api, call, make_db, write_files
from . import ops  # noqa: F401  测试专用算子注册

__all__ = ["ROOT", "CONF", "DATA", "SERVER_YAML", "TempConfCase", "api", "call",
           "make_db", "write_files"]
