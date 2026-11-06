"""字段声明与校验：全框架共用的配置 schema 机制（规则只有一份，各层行为一致）。"""
from __future__ import annotations

import copy
import difflib
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, Type, Union

from .errors import ConfigError

TypeSpec = Union[Type, Tuple[Type, ...]]

_TYPE_NAMES = {str: "string", int: "int", float: "float", bool: "bool",
               dict: "object", list: "list", object: "any"}


@dataclass(frozen=True)
class Field:
    """一个配置字段的声明。

    type      允许的 Python 类型（或元组）；object 表示任意类型
    required  是否必填
    default   缺省值（可变对象每次深拷贝，避免多个节点共享同一份）
    choices   可选值白名单
    dynamic   仅对算子 config 有意义：True 表示该字段支持 {{ }} 模板，每次请求渲染
    raw       仅对算子 config 有意义：True 表示值里可以有 {{ }}，但由算子自己渲染（框架不编译、不校验引用）
    desc      说明，用于 /_operators 文档
    """

    type: TypeSpec = str
    required: bool = False
    default: Any = None
    choices: Optional[Sequence[Any]] = None
    dynamic: bool = False
    desc: str = ""
    raw: bool = False

    @property
    def type_name(self) -> str:
        types = self.type if isinstance(self.type, tuple) else (self.type,)
        return "/".join(_TYPE_NAMES.get(t, t.__name__) for t in types)

    def describe(self) -> Dict[str, Any]:
        """导出为可 JSON 序列化的说明（/_operators 使用）。"""
        return {"type": self.type_name, "required": self.required, "default": self.default,
                "choices": list(self.choices) if self.choices else None,
                "dynamic": self.dynamic, "raw": self.raw, "desc": self.desc}


def child(where: str, key: Union[str, int]) -> str:
    """拼接出错位置：'user/list.yaml' → 'user/list.yaml › graph' → 'user/list.yaml › graph[0].config'。"""
    if isinstance(key, int):
        return f"{where}[{key}]"
    return f"{where}.{key}" if " › " in where else f"{where} › {key}"


def suggest(word: str, candidates: Sequence[str]) -> str:
    """生成 did-you-mean 提示；没有相近项时列出全部可选值。"""
    close = difflib.get_close_matches(word, list(candidates), n=1, cutoff=0.6)
    if close:
        return f", did you mean {close[0]!r}?"
    return f" (available: {', '.join(candidates)})" if candidates else ""


def kind_of(value: Any) -> str:
    """值的类型名（英文），用于报错。"""
    for t in (bool, int, float, str, dict, list):
        if isinstance(value, t):
            return _TYPE_NAMES[t]
    return type(value).__name__


def is_template(value: Any) -> bool:
    """值（含嵌套结构）里是否写了 {{ }} / {% %} 模板。"""
    if isinstance(value, str):
        return "{{" in value or "{%" in value
    if isinstance(value, dict):
        return any(is_template(v) for v in value.values())
    if isinstance(value, list):
        return any(is_template(v) for v in value)
    return False


def check_type(value: Any, field: Field, where: str) -> None:
    """按 Field.type 校验类型。bool 不会被当成 int；float 字段接受 int。"""
    types = field.type if isinstance(field.type, tuple) else (field.type,)
    if object in types:
        return
    if isinstance(value, bool):
        ok = bool in types
    elif isinstance(value, int) and float in types:
        ok = True
    else:
        ok = isinstance(value, types)
    if not ok:
        raise ConfigError(f"expected {field.type_name}, got {kind_of(value)}: {value!r}", where)


def validate(data: Any, spec: Mapping[str, Field], where: str) -> Dict[str, Any]:
    """按 spec 校验映射，返回补齐默认值后的新 dict（dynamic 模板字符串跳过类型检查）。"""
    if data is None:
        data = {}
    if not isinstance(data, Mapping):
        raise ConfigError(f"expected a mapping, got {kind_of(data)}", where)

    for key in data:
        if key not in spec:
            raise ConfigError(f"unknown field {key!r}{suggest(str(key), list(spec))}", where)

    out: Dict[str, Any] = {}
    for key, field in spec.items():
        path = child(where, key)
        value = data.get(key)
        if value is None:
            if field.required:
                raise ConfigError("missing required field", path)
            out[key] = copy.deepcopy(field.default)
            continue
        if field.dynamic and isinstance(value, str) and is_template(value):
            out[key] = value
            continue
        check_type(value, field, path)
        if field.choices is not None and value not in field.choices:
            raise ConfigError(f"invalid value {value!r}{suggest(str(value), [str(c) for c in field.choices])}", path)
        out[key] = value
    return out
