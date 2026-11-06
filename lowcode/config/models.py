"""配置模型：四层（server / group / api / 节点）+ 入参 的字段声明与数据类。

- *_SPEC：YAML 中允许出现的字段，它本身就是配置规范（见 docs/DESIGN.md §3）。
- *Def  ：校验后的静态模型，供 builder 编译成执行计划。
- YAML 键用 camelCase（与 datamore_lite 一致），Python 属性用 snake_case。

文件与层的对应关系（一层一个文件，文件名即路由）：
    server.yaml                        第一层 Server：公共配置
    {module}_{group}.yaml              第二层 Group：分组配置（可选）
    {module}_{group}_{api}.yaml        第三层 API：一个文件一个接口
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..spec import Field

METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")
INPUT_TYPES = ("string", "int", "float", "bool", "list", "object")
TYPE_ALIASES = {"str": "string", "integer": "int", "number": "float",
                "boolean": "bool", "array": "list", "dict": "object"}
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
_NUM = (int, float)

# ---------------------------------------------------------------- 第一层：server.yaml
SERVER_FILE_SPEC = {
    "name": Field(str, default="lowcode", desc="服务名"),
    "server": Field(dict, default={}, desc="服务器参数"),
    "dataSources": Field(list, default=[], desc="数据源列表：{name, type, config}，字段结构与 datamore_lite 对齐"),
}
# 单个数据源条目：config 里是该 type 自己的参数，由数据源层按各自 spec 校验
DATASOURCE_ENTRY_SPEC = {
    "name": Field(str, required=True, desc="数据源名，算子按它引用；同名可跨类别（如同名 redis 与 mysql）"),
    "type": Field(str, required=True, desc="实现类型（sqlite / mysql / http / redis）"),
    "config": Field(dict, default={}, desc="该类型的连接参数"),
}
SERVER_SPEC = {
    "host": Field(str, default="127.0.0.1"),
    "port": Field(int, default=8080),
    "prefix": Field(str, default="", desc="全局路由前缀"),
    "timeout": Field(_NUM, default=10, desc="默认接口超时（秒）"),
    "parallel": Field(bool, default=True, desc="同层节点是否并行"),
    "workers": Field(int, default=8, desc="并行线程池大小"),
    "debug": Field(bool, default=False, desc="5xx 返回详细错误（生产建议关闭）；节点耗时始终写服务端日志"),
    "meta": Field(bool, default=True, desc="开放 /_apis、/_operators"),
    "logLevel": Field(str, default="INFO", choices=LOG_LEVELS),
    "logFile": Field(str, default="", desc="日志文件路径（相对配置根目录）；空 = 只输出到控制台"),
    "logBackup": Field(int, default=7, desc="按天切分保留的天数"),
}

# ---------------------------------------------------------------- 第二层：{module}_{group}.yaml
# 文件名两段即分组标识；路由前缀由文件名拼成 /{module}/{group}，不再允许覆盖
GROUP_SPEC = {
    "name": Field(str, desc="分组显示名，默认分组名"),
    "desc": Field(str, default=""),
    "dataSource": Field(str, desc="本组算子的默认数据源"),
    "timeout": Field(_NUM, desc="本组接口默认超时（秒）"),
}

# ---------------------------------------------------------------- 第三层：{module}_{group}_{api}.yaml
# 接口契约与 datamore_lite 的 APIDef 对齐；path 显式声明完整路由，前三段须与文件名一致
API_SPEC = {
    "name": Field(str, required=True, desc="接口显示名"),
    "method": Field(str, required=True, choices=METHODS),
    "desc": Field(str, required=True, desc="接口说明"),
    "path": Field(str, required=True, desc="接口完整路径；pathOverride=true 时不受文件名前缀约束"),
    "pathOverride": Field(bool, default=False, desc="允许完整路径不受文件名前缀约束，用于兼容旧路由"),
    "timeout": Field(_NUM, desc="接口超时（秒），默认继承分组 / server"),
    "inputs": Field(list, required=True, desc="入参声明（运行时生效），可为空列表"),
    "outputs": Field(list, required=True, desc="响应字段声明：{name, type, desc}；结果节点为 respBuilder 且模板为对象时启动期对账"),
    "graph": Field(list, required=True, desc="算子节点列表，最后一个节点的输出即响应 data"),
}
INPUT_SPEC = {
    "name": Field(str, required=True),
    "type": Field(str, required=True, choices=INPUT_TYPES + tuple(TYPE_ALIASES)),
    "required": Field(bool, default=False),
    "default": Field(object),
    "desc": Field(str, required=True),
    "regex": Field(str, desc="正则（仅 string）"),
    "enum": Field(list, desc="取值白名单"),
    "min": Field(_NUM, desc="数值比大小；string / list 比长度"),
    "max": Field(_NUM),
}
OUTPUT_SPEC = {
    "name": Field(str, required=True, desc="响应字段名"),
    "type": Field(str, required=True, desc="类型说明（自由文本，如 object / list / int；作文档与 /_apis 展示）"),
    "desc": Field(str, required=True, desc="字段说明"),
}

# ---------------------------------------------------------------- 第四层：graph[] 节点
NODE_SPEC = {
    "name": Field(str, required=True, desc="算子注册名"),
    "id": Field((str, int), desc="节点 id，默认等于 name"),
    "depends": Field(list, desc="上游节点 id；不写 = 依赖上一个节点，[] = 根节点"),
    "desc": Field(str, default="", desc="一句话说明本节点做什么；显示在 /_apis、请求日志与 explain 输出中"),
    "config": Field(dict, default={}, desc="算子参数，字段由算子 spec 决定"),
}


@dataclass
class OutputDef:
    """响应字段声明（datamore_lite 的 outputs）：文档契约，结果节点为 respBuilder 时启动期对账。"""

    name: str
    type: str
    desc: str
    where: str = ""


@dataclass
class InputDef:
    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    desc: str = ""
    regex: Optional[str] = None
    enum: Optional[List[Any]] = None
    min: Optional[float] = None
    max: Optional[float] = None
    where: str = ""


@dataclass
class NodeDef:
    name: str                       # 算子注册名（沿用 datamore_lite：节点 name 即算子名）
    id: Optional[str]               # None = 未写，builder 补为 name
    depends: Optional[List[str]]    # None = 未写，builder 补为"上一个节点"
    config: Dict[str, Any]
    desc: str = ""                  # 节点业务说明（可选）
    where: str = ""


@dataclass
class ApiDef:
    name: str
    method: str
    path: str                       # 接口完整路径：/{module}/{group}/{api}[...]，必须与文件名一致
    desc: str
    timeout: Optional[float]
    inputs: List[InputDef]
    outputs: List[OutputDef]
    graph: List[NodeDef]
    slug: str = ""                  # 接口名（文件名第 3 段），path 前三段须与它一致
    where: str = ""                 # 相对配置根目录的文件路径，用于报错定位


@dataclass
class GroupDef:
    module: str                     # 模块名（文件名第 1 段）
    group: str                      # 分组名（文件名第 2 段）
    name: str                       # 分组显示名
    desc: str = ""
    data_source: Optional[str] = None
    timeout: Optional[float] = None
    apis: List[ApiDef] = field(default_factory=list)

    @property
    def key(self) -> str:
        """分组标识，与文件名前两段一致：user_profile。"""
        return f"{self.module}_{self.group}"

    @property
    def prefix(self) -> str:
        """分组路由前缀由文件名决定，不可配置：/user/profile。"""
        return f"/{self.module}/{self.group}"


@dataclass
class ServerDef:
    name: str
    host: str
    port: int
    prefix: str
    timeout: float
    parallel: bool
    workers: int
    debug: bool
    meta: bool
    log_level: str
    data_sources: List[Dict[str, Any]]  # 已校验的 {name, type, config} 条目
    root: Path                      # 配置根目录（server.yaml 所在目录），相对路径以它为基准
    groups: List[GroupDef] = field(default_factory=list)
    log_file: str = ""              # 空 = 只输出到控制台
    log_backup: int = 7             # 按天切分保留天数

    @property
    def apis(self) -> List[ApiDef]:
        return [api for g in self.groups for api in g.apis]
