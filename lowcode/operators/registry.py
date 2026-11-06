"""算子注册表：注册 → 查找 → 创建。重名直接报错；config 由 spec 统一校验。"""
from __future__ import annotations

import inspect
import re
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Type, TypeVar

from ..errors import ConfigError
from ..spec import Field, child, is_template, suggest, validate
from .base import Operator

if TYPE_CHECKING:
    from ..core.builder import BuildEnv

_NAME = re.compile(r"^[a-z][A-Za-z0-9]*$")  # camelCase，与 datamore_lite 的 paramChecker / respBuilder 一致
_operators: Dict[str, Type[Operator]] = {}
T = TypeVar("T", bound=Type[Operator])


def register(name: str, category: str = "custom", desc: str = "") -> Callable[[T], T]:
    """类装饰器：登记算子。这里的错误属于算子代码有误，抛 TypeError / ValueError 在导入时暴露。"""

    def decorator(cls: T) -> T:
        if not (isinstance(cls, type) and issubclass(cls, Operator)):
            raise TypeError(f"@register({name!r}) must decorate an Operator subclass")
        if not _NAME.match(name):
            raise ValueError(f"invalid operator name {name!r}: use camelCase, e.g. sqlQuery")
        old = _operators.get(name)
        if old is not None and old is not cls:
            raise ValueError(f"duplicate operator {name!r}: {_qualname(old)} vs {_qualname(cls)}")
        for key, f in cls.spec.items():
            if not isinstance(f, Field):
                raise TypeError(f"operator {name!r} spec[{key!r}] must be a Field")
            if f.required and f.default is not None:
                raise ValueError(f"operator {name!r} spec[{key!r}] cannot be both required and have a default")

        cls.name = name
        cls.category = category
        cls.desc = desc or (inspect.getdoc(cls) or "").split("\n")[0]
        _operators[name] = cls
        return cls

    return decorator


def get_operator(name: str, where: str = "") -> Type[Operator]:
    """按注册名查找算子类；未知时给出近似名建议。"""
    cls = _operators.get(name)
    if cls is None:
        raise ConfigError(f"unknown operator {name!r}{suggest(name, sorted(_operators))}", child(where, "name"))
    return cls


def list_operators() -> List[Type[Operator]]:
    """所有已注册算子，按分类、名字排序。"""
    return sorted(_operators.values(), key=lambda c: (c.category, c.name))


def create_operator(name: str, node_id: str, config: Dict[str, Any], env: "BuildEnv") -> Operator:
    """工厂：查表 → 拒绝非 dynamic 字段写模板（杜绝 SQL 注入）→ 按 spec 校验 → build() 异常带定位。"""
    cls = get_operator(name, env.where)
    where = child(env.where, "config")
    if isinstance(config, dict):
        for key, f in cls.spec.items():
            if not f.dynamic and not f.raw and is_template(config.get(key)):
                raise ConfigError(f"field {key} does not support {{{{ }}}} templates(only dynamic fields do; see /_operators)",
                                  child(where, key))
    conf = validate(config, cls.spec, where)
    op = cls(node_id, conf, env)
    try:
        op.build()
    except ConfigError:
        raise
    except Exception as e:  # noqa: BLE001  任何构建期异常都要带上定位
        raise ConfigError(f"operator {name} build failed: {type(e).__name__}: {e}", env.where) from e
    return op


def _qualname(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"
