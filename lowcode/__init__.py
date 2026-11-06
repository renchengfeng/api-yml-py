"""lowcode —— YAML 驱动的 Flask 低代码 HTTP 框架。

    from lowcode import create_app
    app = create_app("conf")            # conf/ 下：server.yaml + 每个分组一个目录 + 每个接口一个文件

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
from .web import create_app

__version__ = "0.1.0"
__all__ = ["create_app", "Field", "Operator", "register", "LowcodeError", "ConfigError", "BizError"]
