"""编译器：ApiDef → ApiPlan。启动期执行一次，运行期只做模板渲染。"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from ..config.models import ApiDef, GroupDef, InputDef, NodeDef, ServerDef
from ..datasources import DataSource, DataSourceManager
from ..errors import ConfigError, ErrorCollector
from ..operators import Operator, create_operator
from ..spec import child, is_template, suggest
from .graph import Graph
from .inputs import InputSchema
from .template import GLOBALS, Template, compile_template

RESERVED_IDS = frozenset({"inputs", "request"})  # 模板命名空间里的保留名，不能用作节点 id
_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PATH_PARAM = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_PATH_CHARS = re.compile(r"^[A-Za-z0-9_\-./~{}]*$")


@dataclass
class PlanNode:
    """计划中的一个节点：算子实例 + 静态参数 + 已编译的动态参数。"""

    id: str
    op: Operator
    depends: Tuple[str, ...]
    static: Dict[str, Any]
    dynamic: Dict[str, Template]
    desc: str = ""                  # 节点业务说明（配置里的 desc）

    @property
    def effective_desc(self) -> str:
        return self.desc or self.op.desc  # 节点 desc 优先，缺省回退算子说明

    def resolve_args(self, scope: Dict[str, Any]) -> Dict[str, Any]:
        """本次请求的 args：静态字段原样返回，动态字段按 scope 渲染。"""
        if not self.dynamic:
            return self.static
        args = dict(self.static)
        for key, tpl in self.dynamic.items():
            args[key] = tpl.render(scope)
        return args


@dataclass
class ApiPlan:
    """一个接口的执行计划。"""

    api: ApiDef
    group: GroupDef
    url: str                    # 对外展示：/api/user/{uid}
    rule: str                   # Flask 规则：/api/user/<uid>
    inputs: InputSchema
    nodes: Dict[str, PlanNode]
    levels: List[List[str]]     # 拓扑分层，同层可并行
    result: str                 # 结果节点 id（graph 最后一个节点）
    timeout: float

    @property
    def method(self) -> str:
        return self.api.method

    @property
    def key(self) -> str:
        return f"{self.method} {self.url}"


class BuildEnv:
    """算子 build() 期间可用的环境：取数据源、知道自己的位置（用于报错）。"""

    def __init__(self, datasources: DataSourceManager, group: GroupDef, where: str):
        self._datasources = datasources
        self.group = group
        self.where = where

    def datasource(self, name: Optional[str], kind: str) -> DataSource:
        """解析顺序：节点 config.dataSource → 分组 dataSource（类别相符时）→ 该类别唯一的数据源。
        解析成功即确认可选依赖已安装，缺包在编译该接口时暴露，不等到首次请求。"""
        where = child(child(self.where, "config"), "dataSource")
        if not name:
            group_default = self.group.data_source
            if group_default and self._datasources.has(group_default, kind):
                name = group_default
        ds = self._datasources.resolve(name, kind, where)
        ds.check_dependencies()
        return ds


class Builder:
    def __init__(self, server: ServerDef, datasources: DataSourceManager):
        self.server = server
        self.datasources = datasources

    def build(self, errors: Optional[ErrorCollector] = None) -> List[ApiPlan]:
        """编译全部接口；错误按接口收集。未传 errors 时收集完一次性抛出，传入时追加进去。"""
        collector = errors if errors is not None else ErrorCollector()
        plans: List[ApiPlan] = []
        routes: Dict[str, str] = {}
        for group in self.server.groups:
            with collector.collect():
                self._check_group(group)
            for api in group.apis:
                with collector.collect():
                    plan = self.build_api(group, api)
                    if plan.key in routes:
                        raise ConfigError(f"duplicate route {plan.key} (already in {routes[plan.key]})", api.where)
                    routes[plan.key] = api.where
                    plans.append(plan)
        if errors is None:
            collector.raise_if_any()
        return plans

    def build_api(self, group: GroupDef, api: ApiDef) -> ApiPlan:
        url = self._url(api)
        inputs = InputSchema(_with_path_params(api, url), child(api.where, "inputs"))

        defs = _resolve_nodes(api)
        graph = Graph({n.id: n.depends for n in defs}, child(api.where, "graph"))
        levels = graph.levels()
        result = defs[-1].id
        _check_reachable(defs, graph, result)

        all_ids = {n.id for n in defs}
        nodes: Dict[str, PlanNode] = {}
        for n in defs:
            env = BuildEnv(self.datasources, group, n.where)
            nodes[n.id] = compile_node(n, env, graph.ancestors(n.id), all_ids, inputs.names)

        timeout = next(t for t in (api.timeout, group.timeout, self.server.timeout) if t is not None)
        if timeout <= 0:
            raise ConfigError(f"timeout must be > 0, got {timeout}", api.where)
        _check_outputs(api, nodes[result])
        return ApiPlan(api=api, group=group, url=url, rule=_PATH_PARAM.sub(r"<\1>", url),
                       inputs=inputs, nodes=nodes, levels=levels, result=result, timeout=timeout)

    def _check_group(self, group: GroupDef) -> None:
        name = group.data_source
        if name and self.datasources.get(name) is None:
            names = sorted(ds.name for ds in self.datasources.items())
            raise ConfigError(f"datasource {name!r} not found{suggest(name, names)}", f"{group.key}.yaml › dataSource")

    def _url(self, api: ApiDef) -> str:
        """URL = server.prefix + 接口显式声明的 path（path 前三段已按文件名校验过）。"""
        parts = [(self.server.prefix, "server.yaml › server.prefix"),
                 (api.path, child(api.where, "path"))]
        for value, where in parts:
            if "<" in value or ">" in value:
                raise ConfigError(f"invalid path {value!r}: path parameters must be written as {{{{name}}}}", where)
            rest = _PATH_PARAM.sub("", value)  # 去掉合法的 {name} 后不应再有花括号
            if not _PATH_CHARS.match(value) or "{" in rest or "}" in rest:
                raise ConfigError(f"invalid path {value!r}: illegal characters", where)
        segments = (p.strip("/") for p, _ in parts)
        return "/" + "/".join(s for s in segments if s)


def compile_node(node: NodeDef, env: BuildEnv, ancestors: Set[str], all_ids: Set[str],
                 input_names: Sequence[str]) -> PlanNode:
    """编译单个节点（id / depends 须已补齐）。与算子测试框架共用，保证测试路径 = 线上路径。"""
    op = create_operator(node.name, node.id, node.config, env)
    static, dynamic = _compile_config(op, node, ancestors, all_ids, input_names)
    return PlanNode(node.id, op, tuple(node.depends), static, dynamic, desc=node.desc)

def _check_outputs(api: ApiDef, result: PlanNode) -> None:
    """outputs 对账：结果节点为 respBuilder 且模板为对象时，模板键必须覆盖所有声明（其余仅作文档）。"""
    if not api.outputs or result.op.name != "respBuilder":
        return
    data = result.op.config.get("data")
    if not isinstance(data, dict):
        return
    missing = [o.name for o in api.outputs if o.name not in data]
    if missing:
        raise ConfigError(f"output {missing[0]!r} is missing from the response data"
                          f"(data keys: {', '.join(data)})", child(api.where, "outputs"))


def _skeleton(value: Any) -> Any:
    """把 respBuilder 的模板值转成响应结构骨架：动态表达式记为 "…"，列表取首个元素的结构。"""
    if isinstance(value, str):
        return "…" if is_template(value) else value
    if isinstance(value, dict):
        return {k: _skeleton(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_skeleton(value[0])] if value else []
    return value


def response_shape(plan: ApiPlan) -> Optional[Any]:
    """推断响应结构骨架（仅结果节点为 respBuilder 时可得），供 /_apis 与 explain 展示。"""
    op = plan.nodes[plan.result].op
    data = op.config.get("data")
    if op.name != "respBuilder" or data is None:
        return None
    return _skeleton(data)


def _with_path_params(api: ApiDef, url: str) -> List[InputDef]:
    """路径参数若未在 inputs 中声明，自动补成必填 string。"""
    params = _PATH_PARAM.findall(url)
    if len(params) != len(set(params)):
        raise ConfigError(f"duplicate path parameter: {url}", child(api.where, "path"))
    declared = {d.name for d in api.inputs}
    extra = [InputDef(name=p, type="string", required=True, desc="路径参数", where=child(api.where, "path"))
             for p in params if p not in declared]
    return list(api.inputs) + extra


def _resolve_nodes(api: ApiDef) -> List[NodeDef]:
    """补齐缺省：id 默认等于算子名，depends 默认依赖上一个节点。"""
    ids: List[str] = []
    for n in api.graph:
        nid = n.id or n.name
        if not _ID.match(nid):
            raise ConfigError(f"invalid node id {nid!r}: must be an identifier (referenced as {{{{ id.field }}}})", n.where)
        if nid in RESERVED_IDS:
            raise ConfigError(f"node id {nid!r} is reserved ({', '.join(sorted(RESERVED_IDS))}）", n.where)
        if nid in ids:
            hint = "; give each node an explicit id when the same operator appears more than once" if n.id is None else ""
            raise ConfigError(f"duplicate node id {nid!r}{hint}", n.where)
        ids.append(nid)

    resolved = []
    for i, (n, nid) in enumerate(zip(api.graph, ids)):
        deps = n.depends if n.depends is not None else ([ids[i - 1]] if i else [])
        where = child(n.where, "depends")
        if len(set(deps)) != len(deps):
            raise ConfigError("duplicate entries in depends", where)
        for dep in deps:
            if dep == nid:
                raise ConfigError("a node cannot depend on itself", where)
            if dep not in ids:
                raise ConfigError(f"unknown dependency {dep!r}{suggest(dep, ids)}", where)
        resolved.append(replace(n, id=nid, depends=list(deps)))
    return resolved


def _check_reachable(defs: List[NodeDef], graph: Graph, result: str) -> None:
    """除结果节点外，每个节点都必须是它的上游，否则其输出不会进入响应。"""
    needed = graph.ancestors(result) | {result}
    for n in defs:
        if n.id not in needed:
            raise ConfigError(f"节点 {n.id!r} never reaches the result node {result!r}(the last node): "
                              f"add it to a downstream depends, or remove it", n.where)


def _compile_config(op: Operator, node: NodeDef, ancestors: Set[str], all_ids: Set[str],
                    input_names: Sequence[str]) -> Tuple[Dict[str, Any], Dict[str, Template]]:
    """把 config 拆成静态参数与动态模板（非 dynamic 字段写模板已在 create_operator 中拒绝）。"""
    static: Dict[str, Any] = {}
    dynamic: Dict[str, Template] = {}
    for key, field in op.spec.items():
        value = op.config[key]
        if not field.dynamic:
            static[key] = value
            continue
        where = child(child(node.where, "config"), key)
        tpl = compile_template(value, where)
        if tpl.is_static:
            static[key] = value
            continue
        _check_refs(tpl, ancestors, all_ids, input_names, where)
        dynamic[key] = tpl
    return static, dynamic


def _check_refs(tpl: Template, ancestors: Set[str], all_ids: Set[str],
                input_names: Sequence[str], where: str) -> None:
    for name in sorted(tpl.names - RESERVED_IDS - ancestors - GLOBALS):
        if name in all_ids:
            raise ConfigError(f"referenced node {name!r} is not an upstream of this node: add it to depends", where)
        usable = sorted(RESERVED_IDS | ancestors)
        raise ConfigError(f"unknown variable {name!r}{suggest(name, usable)}", where)
    for key in sorted(tpl.inputs - set(input_names)):
        raise ConfigError(f"reference to undeclared input inputs.{key}{suggest(key, list(input_names))}", where)
