"""算子基类。

生命周期：@register 注册 → create_operator 创建（按 spec 校验）→ build() 启动期一次
→ execute(ctx, args) 每请求一次。约束：不得原地修改 args 与上游输出（节点间共享）。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional

from ..errors import ConfigError
from ..spec import Field, child

if TYPE_CHECKING:  # 仅用于类型标注，避免运行期循环导入
    from ..core.builder import BuildEnv
    from ..core.context import Context


class Operator:
    """所有算子的基类。子类声明 spec 并实现 execute()，按需实现 build()。"""

    name: ClassVar[str] = ""                 # 注册名，由 @register 写入
    category: ClassVar[str] = "custom"       # 分类：filter / transformer / external（custom 为缺省）
    desc: ClassVar[str] = ""                 # 说明，缺省取类 docstring 首行
    spec: ClassVar[Dict[str, Field]] = {}    # config 字段声明

    def __init__(self, node_id: str, config: Dict[str, Any], env: "BuildEnv"):
        self.id = node_id      # 节点 id
        self.config = config   # 已按 spec 校验并补齐默认值；dynamic 字段此时仍是原始模板
        self.env = env         # 构建期环境：取数据源、报错定位

    def build(self) -> None:
        """启动期调用一次：把能提前做的事都做掉，让错误在启动时暴露。"""

    def execute(self, ctx: "Context", args: Dict[str, Any]) -> Any:
        """处理一次请求。args 是渲染后的 config（dynamic 字段已取值）。"""
        raise NotImplementedError(f"算子 {self.name} 未实现 execute()")

    def config_error(self, msg: str, key: Optional[str] = None) -> ConfigError:
        """构造一个带定位的配置错误（build() 中使用：raise self.config_error(...)）。"""
        where = child(self.env.where, "config")
        return ConfigError(msg, child(where, key) if key else where)

    @classmethod
    def describe(cls) -> Dict[str, Any]:
        """导出算子说明（/_operators 与 CLI 使用）。"""
        return {"name": cls.name, "category": cls.category, "desc": cls.desc,
                "config": {k: f.describe() for k, f in cls.spec.items()}}
