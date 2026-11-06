"""算子层：编写算子所需的全部 API。

6 个分类按顺序判定，任何算子只归入一类：

    external     读写框架外部资源（usql / uhttp / uredis / ufs）
    filter       条件不满足即中断请求
    aggregate    多行归约成统计量
    validate     按规则检查并输出报告，不中断
    selector     只选取 / 投影 / 重命名 / 二选一
    transformer  其余纯数据变换（无外部 I/O）

各分类子包在本文件末尾导入：导入即注册。
"""
from ..spec import Field
from .base import Operator
from .registry import create_operator, get_operator, list_operators, register

__all__ = ["Field", "Operator", "register", "get_operator", "list_operators", "create_operator"]

# 导入各分类，完成内置算子的注册。必须放在末尾：此时基类与注册表已就绪。
from . import aggregate, external, filter, selector, transformer, validate  # noqa: E402,F401
