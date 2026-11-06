"""入参：按 api.inputs 声明做 取值 → 缺省 → 类型转换 → 约束校验（声明即生效，无需额外校验节点）。"""
from __future__ import annotations

import copy
import json
import re
from typing import Any, Dict, List, Mapping, Pattern

from ..config.models import InputDef
from ..errors import ConfigError, ParamError
from ..spec import child

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}
_TYPE_NAMES = {"string": "字符串", "int": "整数", "float": "数字",
               "bool": "布尔", "list": "列表", "object": "对象"}


def coerce(value: Any, type_: str) -> Any:
    """把一个原始值转换为声明的类型；失败抛 ValueError（消息给最终用户看）。

    同时兼容两种来源：query/form 中的字符串（"5"）与 JSON body 中的原生值（5）。
    """
    if type_ == "string":
        if isinstance(value, (dict, list)):
            raise ValueError("应为字符串")
        return value if isinstance(value, str) else str(value)
    if type_ == "int":
        if isinstance(value, bool):
            raise ValueError("应为整数")
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                pass
        raise ValueError("应为整数")
    if type_ == "float":
        if isinstance(value, bool):
            raise ValueError("应为数字")
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).strip())
        except ValueError:
            raise ValueError("应为数字") from None
    if type_ == "bool":
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        raise ValueError("应为布尔（true/false/1/0）")
    if type_ == "list":
        if isinstance(value, list):
            return value
        if isinstance(value, str):  # query 中的 a,b,c
            return [s.strip() for s in value.split(",") if s.strip()]
        raise ValueError("应为列表")
    if type_ == "object":
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("应为对象（JSON）")
    raise ValueError(f"未知类型 {type_}")


class InputSchema:
    """一个接口的入参校验器（启动期构造，请求期复用）。"""

    def __init__(self, defs: List[InputDef], where: str):
        self.defs = defs
        self._regex: Dict[str, Pattern[str]] = {}
        seen = set()
        for d in defs:
            if not _IDENT.match(d.name):
                raise ConfigError(f"invalid input name {d.name!r}: must be an identifier", d.where)
            if d.name in seen:
                raise ConfigError(f"duplicate input {d.name!r}", d.where)
            seen.add(d.name)
            self._check_def(d)

    @property
    def names(self) -> List[str]:
        return [d.name for d in self.defs]

    def _check_def(self, d: InputDef) -> None:
        """启动期检查声明本身：默认值 / 枚举与类型一致、正则可编译。"""
        if d.required and d.default is not None:
            raise ConfigError("required and default are mutually exclusive (a default makes it optional)", d.where)
        if (d.min is not None or d.max is not None) and d.type in ("bool", "object"):
            raise ConfigError(f"min / max cannot be used with type={d.type}", d.where)
        try:
            if d.default is not None:
                d.default = coerce(d.default, d.type)
            if d.enum is not None:
                d.enum = [coerce(v, d.type) for v in d.enum]
        except ValueError as e:
            raise ConfigError(f"default / enum does not match type={d.type}: {e}", d.where) from None
        if d.regex is not None:
            if d.type != "string":
                raise ConfigError("regex is only allowed for type=string", child(d.where, "regex"))
            try:
                self._regex[d.name] = re.compile(d.regex)
            except re.error as e:
                raise ConfigError(f"regex does not compile: {e}", child(d.where, "regex")) from None

    def parse(self, raw: Mapping[str, Any]) -> Dict[str, Any]:
        """校验原始参数，返回只含已声明入参的 dict。所有错误一次列全。"""
        out: Dict[str, Any] = {}
        errors: List[str] = []
        for d in self.defs:
            try:
                out[d.name] = self._parse_one(d, raw.get(d.name))
            except ValueError as e:
                errors.append(f"{d.name} {e}")
        if errors:
            raise ParamError("参数错误：" + "；".join(errors))
        return out

    def _parse_one(self, d: InputDef, value: Any) -> Any:
        if value is None or value == "" or value == []:  # 空串视为未传
            if d.required:
                raise ValueError("必填")
            return copy.deepcopy(d.default)
        v = coerce(value, d.type)
        if d.enum is not None and v not in d.enum:
            raise ValueError(f"取值应为 {d.enum} 之一")
        if d.name in self._regex and not self._regex[d.name].search(v):
            raise ValueError(f"格式不正确（{d.regex}）")
        if d.min is not None or d.max is not None:
            size, unit = (v, "") if d.type in ("int", "float") else (len(v), "长度")
            if d.min is not None and size < d.min:
                raise ValueError(f"{unit}不能小于 {d.min}")
            if d.max is not None and size > d.max:
                raise ValueError(f"{unit}不能大于 {d.max}")
        return v
