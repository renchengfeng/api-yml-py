"""算子层：编写算子所需的全部 API。分类沿用 datamore_lite —— filter / transformer / external / aggregate / selector：

    from lowcode.operators import Field, Operator, register

    filter       校验与断言，条件不满足即中断流程（对应 datamore 的 paramChecker）
    transformer  只加工数据、决定输出形态（对应 datamore 的 respBuilder / respMergeBuilder）
    external     与外部系统交互，按数据源分 usql / uhttp / uredis（对应 datamore 的 external/*）
    aggregate    聚合统计：listAgg / groupBy（补全 datamore 预留的 aggregate/ 目录）
    selector     字段投影：fieldPicker（补全 datamore 预留的 selector/ 目录）
    custom       缺省分类（内置算子不用）

各分类子包在本文件末尾导入：导入即注册（对标 datamore_lite 用空导入触发包级 init()）。
"""
from ..spec import Field
from .base import Operator
from .registry import create_operator, get_operator, list_operators, register

__all__ = ["Field", "Operator", "register", "get_operator", "list_operators", "create_operator"]

# 导入各分类，完成内置算子的注册。必须放在末尾：此时基类与注册表已就绪。
from . import aggregate, external, filter, selector, transformer  # noqa: E402,F401
