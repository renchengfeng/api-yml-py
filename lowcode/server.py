"""库式入口：把 lowcode 当外部库嵌入 Python 项目。

    from lowcode import Lowcode

    server = Lowcode("conf")       # 解析配置、编译接口，失败抛 ConfigError
    server.run()                   # 开发运行（host / port 取自 server.yaml）

    # 生产（WSGI）：
    #   gunicorn -w 4 'main:server'

与 create_app() 的区别：create_app() 只返回 Flask app；Lowcode 把 app、runtime、
生命周期与运行参数收在一个对象里，适合 main.py / 脚本 / 测试使用。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from .runtime import Runtime
from .web.app import create_app


class Lowcode:
    """一次装配好的服务：Flask app + 执行计划 + 生命周期。

    - ``.app``     底层 Flask 应用（需要 Flask 生态时直接用）；
    - ``.runtime`` 完整 Runtime（server / datasources / plans / executor）；
    - ``.run()``   开发服务器，参数缺省取 ``server.yaml``；
    - ``close()``  释放线程池与数据源；也支持 ``with Lowcode(...) as s:``；
    - ``__call__`` 让实例本身可作为 WSGI app（gunicorn 等直接引用 ``main:server``）。
    """

    def __init__(self, conf_dir: Union[str, Path] = "conf", *,
                 host: Optional[str] = None, port: Optional[int] = None) -> None:
        self.app = create_app(conf_dir)
        self.runtime: Runtime = self.app.extensions["lowcode"]
        self.server = self.runtime.server
        self._host = host
        self._port = port

    @property
    def plans(self):
        """编译后的接口计划，调试或生成文档时可直接读。"""
        return self.runtime.plans

    def run(self, host: Optional[str] = None, port: Optional[int] = None,
            debug: bool = False, threaded: bool = True, **kwargs: Any) -> None:
        """启动开发服务器；host / port 缺省取 server.yaml。"""
        self.app.run(host=host or self._host or self.server.host,
                     port=port or self._port or self.server.port,
                     debug=debug, threaded=threaded, **kwargs)

    def close(self) -> None:
        self.runtime.close()

    def __enter__(self) -> "Lowcode":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def __call__(self, environ: dict, start_response):
        """WSGI 入口：``gunicorn 'main:server'`` 无需再取 ``.app``。"""
        return self.app(environ, start_response)


def create_server(conf_dir: Union[str, Path] = "conf", **kwargs: Any) -> Lowcode:
    """``Lowcode(conf_dir, **kwargs)`` 的函数式写法。"""
    return Lowcode(conf_dir, **kwargs)
