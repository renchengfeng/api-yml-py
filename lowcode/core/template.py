"""模板：配置中 {{ }} 的编译与求值。

语法为 Jinja2 表达式（沙箱模式），只在算子 spec 中声明为 dynamic 的字段里生效：

    "{{ inputs.page }}"                 整串只有一个表达式 → 保留原生类型（int 仍是 int）
    "第 {{ inputs.page }} 页"            与文字混排 → 渲染为字符串
    "{{ (inputs.page - 1) * inputs.size }}"   支持表达式
    {list: "{{ rows }}", n: 1}          dict / list 递归编译

取值失败（键不存在）直接报错，不静默变成空串；需要兜底请写 {{ x.y | default(0) }}。
命名空间：inputs（已校验入参）、request（请求信息）、<节点id>（上游节点输出）。
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Dict, FrozenSet, Iterable, Tuple

from jinja2 import StrictUndefined, TemplateError, Undefined, meta, nodes
from jinja2.sandbox import SandboxedEnvironment

from ..errors import ConfigError, ExecError

# 整串恰好是一个 {{ ... }}，且内部不再包含 {{ / }}
_WHOLE = re.compile(r"^\s*\{\{(?P<expr>(?:(?!\{\{|\}\}).)*)\}\}\s*$", re.S)


class _Env(SandboxedEnvironment):
    """字典优先按键取值：{{ row.items }} 取名为 items 的列，而不是 dict.items 方法。"""

    def getattr(self, obj: Any, attribute: str) -> Any:
        if isinstance(obj, Mapping) and attribute in obj:
            return obj[attribute]
        return super().getattr(obj, attribute)


_ENV = _Env(undefined=StrictUndefined, autoescape=False, keep_trailing_newline=True)
GLOBALS: FrozenSet[str] = frozenset(_ENV.globals)  # range / dict 等内置全局名，引用检查时放行


class Template:
    """已编译的模板值。

    names   引用到的顶层变量名（inputs / request / 节点 id / 全局函数）
    inputs  引用到的 inputs.<key>，供启动期核对入参是否已声明
    """

    names: FrozenSet[str] = frozenset()
    inputs: FrozenSet[str] = frozenset()
    is_static = False

    def render(self, scope: Dict[str, Any]) -> Any:
        raise NotImplementedError


class _Const(Template):
    is_static = True

    def __init__(self, value: Any):
        self.value = value

    def render(self, scope: Dict[str, Any]) -> Any:
        return self.value


class _Expr(Template):
    """单个表达式：返回原生类型。"""

    def __init__(self, source: str, where: str):
        self.source = source.strip()
        try:
            self._fn = _ENV.compile_expression(self.source, undefined_to_none=False)
            self.names, self.inputs = _analyze("{{ " + self.source + " }}")
        except TemplateError as e:
            raise ConfigError(f"template syntax error {{{{ {self.source} }}}}: {e}", where) from None

    def render(self, scope: Dict[str, Any]) -> Any:
        try:
            value = self._fn(**scope)
        except TemplateError as e:
            raise ExecError(f"template evaluation failed {{{{ {self.source} }}}}: {e}") from None
        if isinstance(value, Undefined):
            raise ExecError(f"template lookup failed {{{{ {self.source} }}}}: value does not exist (use | default(...) as fallback)")
        return value


class _Text(Template):
    """文字与表达式混排：渲染为字符串。"""

    def __init__(self, source: str, where: str):
        self.source = source
        try:
            self._tpl = _ENV.from_string(source)
            self.names, self.inputs = _analyze(source)
        except TemplateError as e:
            raise ConfigError(f"template syntax error {source!r}: {e}", where) from None

    def render(self, scope: Dict[str, Any]) -> Any:
        try:
            return self._tpl.render(scope)
        except TemplateError as e:
            raise ExecError(f"template render failed {self.source!r}: {e}") from None


class _Composite(Template):
    """dict / list：逐项渲染。"""

    def __init__(self, items: Iterable[Tuple[Any, Template]], is_dict: bool):
        self.items = list(items)
        self.is_dict = is_dict
        self.is_static = all(t.is_static for _, t in self.items)
        self.names = frozenset().union(*(t.names for _, t in self.items))
        self.inputs = frozenset().union(*(t.inputs for _, t in self.items))

    def render(self, scope: Dict[str, Any]) -> Any:
        if self.is_dict:
            return {k: t.render(scope) for k, t in self.items}
        return [t.render(scope) for _, t in self.items]


def compile_template(value: Any, where: str) -> Template:
    """把配置值编译成 Template（启动期调用，语法错误抛 ConfigError）。"""
    if isinstance(value, str):
        if "{{" not in value and "{%" not in value:
            return _Const(value)
        m = _WHOLE.match(value)
        return _Expr(m.group("expr"), where) if m else _Text(value, where)
    if isinstance(value, dict):
        return _Composite(((k, compile_template(v, f"{where}.{k}")) for k, v in value.items()), True)
    if isinstance(value, list):
        return _Composite(((i, compile_template(v, f"{where}[{i}]")) for i, v in enumerate(value)), False)
    return _Const(value)


def _analyze(source: str) -> Tuple[FrozenSet[str], FrozenSet[str]]:
    """静态分析模板：引用了哪些顶层变量、哪些 inputs.<key>。"""
    ast = _ENV.parse(source)
    names = frozenset(meta.find_undeclared_variables(ast))
    keys = set()
    for n in ast.find_all((nodes.Getattr, nodes.Getitem)):
        if isinstance(n.node, nodes.Name) and n.node.name == "inputs":
            if isinstance(n, nodes.Getattr):
                keys.add(n.attr)
            elif isinstance(n.arg, nodes.Const) and isinstance(n.arg.value, str):
                keys.add(n.arg.value)
    return names, frozenset(keys)
