"""Redis 数据源（依赖 redis-py；缺包在编译接口时报错，连接延迟到首次使用）。

支持两种 config 写法：
    config: {url: "redis://:password@host:6379/0", timeout: 3}
    config: {address: "dns://localhost:6379", password: "12345678", db: 0}   # datamore_lite 风格
注意：timeout 单位为秒（datamore_lite 为毫秒，迁移时需换算）。
"""
from __future__ import annotations

import threading
from importlib.util import find_spec
from typing import Dict, List, Optional
from urllib.parse import quote

from ..errors import ConfigError
from ..spec import Field, child
from . import DataSource, register_datasource


@register_datasource("redis")
class RedisDataSource(DataSource):
    """redis-py 客户端自带线程安全的连接池，进程内共享一个即可（首次使用时创建）。"""

    kind = "kv"
    spec = {
        "url": Field(str, desc="redis://[:password@]host:port/db；与 address 二选一"),
        "address": Field(str, desc="datamore 风格地址：dns://host:port 或 host:port；与 url 二选一"),
        "password": Field(str, default="", desc="配合 address 使用；url 中可内嵌密码"),
        "db": Field(int, default=0, desc="库编号，配合 address 使用"),
        "timeout": Field((int, float), default=3, desc="连接 / 读写超时（秒）"),
    }

    def check(self) -> None:
        """启动期自检：配置完整性；不建立连接，连接延迟到首次使用。"""
        if not self.config["url"] and not self.config["address"]:
            raise ConfigError("set either url or address", child(self.where, "url"))
        self._client = None
        self._lock = threading.Lock()

    def check_dependencies(self) -> None:
        """redis-py 缺失时抛错：编译使用本数据源的接口时触发，启动期即暴露。"""
        if find_spec("redis") is None:
            raise ConfigError('redis datasource requires redis-py: pip install "api-yml-py[redis]"', self.where)

    def _connect_url(self) -> str:
        if self.config["url"]:
            return self.config["url"]
        host = self.config["address"].removeprefix("dns://").removeprefix("redis://")
        password = quote(self.config["password"], safe="") if self.config["password"] else ""
        auth = f":{password}@" if password else ""
        return f"redis://{auth}{host}/{self.config['db']}"

    def _get_client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    try:
                        import redis
                    except ImportError:
                        raise ConfigError('redis datasource requires redis-py: pip install "api-yml-py[redis]"', self.where) from None
                    t = self.config["timeout"]
                    self._client = redis.Redis.from_url(
                        self._connect_url(), socket_timeout=t, socket_connect_timeout=t,
                        decode_responses=True)
        return self._client

    def get(self, key: str) -> Optional[str]:
        return self._get_client().get(key)

    def mget(self, keys: List[str]) -> List[Optional[str]]:
        if not keys:
            return []
        return self._get_client().mget(list(keys))

    def hgetall(self, key: str) -> Dict[str, str]:
        return self._get_client().hgetall(key)

    def close(self) -> None:
        if getattr(self, "_client", None) is not None:
            self._client.close()
