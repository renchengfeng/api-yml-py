"""装配：配置 → 数据源 → 执行计划 → 执行器。

Web 层与 CLI 都只依赖这里的 build_runtime()，彼此互不知道对方。
内置算子（filter / transformer / external）在 lowcode.operators 包导入时即完成注册，
随 lowcode 包加载而就绪，无需额外装配步骤；新增算子直接放进 operators/<分类>/（见算子导航检查清单）。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

from .config import ServerDef, load_config
from .core import ApiPlan, Builder, Executor
from .datasources import DataSourceManager
from .errors import ErrorCollector


@dataclass
class Runtime:
    """一次装配的完整产物。"""

    server: ServerDef
    datasources: DataSourceManager
    plans: List[ApiPlan]
    executor: Executor

    def close(self) -> None:
        self.executor.shutdown()
        self.datasources.close()


def build_runtime(conf_dir: Union[str, Path]) -> Runtime:
    """按启动顺序装配。结构错误与语义错误汇总后一次性抛出（ConfigError.errors 为全部条目）。

    server.yaml 本身、数据源有误时后续步骤无从进行，到此为止；
    单个分组 / 接口文件有误时只跳过它，其余文件继续编译，以便一次暴露全部问题。
    """
    errors = ErrorCollector()
    server = load_config(conf_dir, errors)                                  # ① 配置层：结构校验
    with errors.collect():
        datasources = DataSourceManager.from_config(server.data_sources, server.root)  # ② 数据源：实例化 + 自检
        plans = Builder(server, datasources).build(errors)                  # ③ 编译：ApiDef → ApiPlan
    errors.raise_if_any()
    executor = Executor(server.parallel, server.workers)                    # ④ 执行器
    return Runtime(server, datasources, plans, executor)
