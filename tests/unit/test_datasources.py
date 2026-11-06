"""数据源单测：可选依赖缺失在编译接口时即报错（不等到首次请求才暴露）。"""
import unittest
from unittest.mock import patch

from lowcode.datasources.mysql import MysqlDataSource
from lowcode.datasources.redis import RedisDataSource
from lowcode.errors import ConfigError
from lowcode.spec import validate


def _make(cls, config: dict, where: str = "ds"):
    return cls("ds", validate(config, cls.spec, where), None, where)


class DependencyCheckTest(unittest.TestCase):
    def test_redis_missing_package_fails_at_startup(self):
        ds = _make(RedisDataSource, {"url": "redis://localhost:6379/0"})
        with patch("lowcode.datasources.redis.find_spec", return_value=None):
            with self.assertRaises(ConfigError) as cm:
                ds.check_dependencies()
        self.assertIn('pip install "lowcode[redis]"', str(cm.exception))

    def test_mysql_missing_package_fails_at_startup(self):
        ds = _make(MysqlDataSource, {"sourceName": "root:12345678@tcp(localhost:3306)/datamore"})
        with patch("lowcode.datasources.mysql.find_spec", return_value=None):
            with self.assertRaises(ConfigError) as cm:
                ds.check_dependencies()
        self.assertIn('pip install "lowcode[mysql]"', str(cm.exception))

    def test_installed_package_passes_check_without_connecting(self):
        ds = _make(RedisDataSource, {"url": "redis://localhost:6379/0"})
        ds.check()  # 配置自检通过
        ds.check_dependencies()  # 当前环境已安装 redis-py：依赖检查通过
        self.assertIsNone(ds._client)  # 全程未建立连接
