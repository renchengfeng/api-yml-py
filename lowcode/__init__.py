"""lowcode —— YAML 驱动的 Flask 低代码 HTTP 框架。

作为库使用（推荐）：

    from lowcode import Lowcode
    server = Lowcode("conf")            # 解析配置、编译接口
    server.run()                        # 开发运行；生产用 gunicorn 'main:server'

只想要 Flask app：

    from lowcode import create_app
    app = create_app("conf")

接口全部由内置算子组合而成（filter / transformer / external，见 operator_md/算子导航.md）。
新增算子时在 lowcode/operators/<分类>/ 下定义：

    from lowcode import Field, Operator, register

    @register("hello", category="transformer")
    class Hello(Operator):
        spec = {"name": Field(str, default="world", dynamic=True)}
        def execute(self, ctx, args):
            return f"hello {args['name']}"
"""
from .errors import BizError, ConfigError, LowcodeError
from .operators import Field, Operator, register
from .server import Lowcode, create_server
from .web import create_app
from .web.response import RawResponse

__version__ = "0.1.0"
__all__ = ["Lowcode", "create_server", "create_app", "RawResponse", "Field", "Operator", "register",
           "LowcodeError", "ConfigError", "BizError"]
