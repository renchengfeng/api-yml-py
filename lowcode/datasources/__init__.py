"""数据源层：{name, type, config} 条目（与 datamore_lite 对齐），算子按能力类别（sql/http/kv）取用。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, TypeVar

from ..errors import ConfigError, ErrorCollector
from ..spec import Field, child, suggest, validate  # noqa: F401  Field 供类型标注


class DataSource:
    """数据源基类。子类声明 kind / spec，并按类别实现对应方法：

        sql   query(sql, params) -> List[dict]；execute(sql, params) -> {rowcount, lastrowid}
        http  request(method, url, query=, body=, headers=, timeout=) -> Any
        kv    get(key) -> Optional[str]；hgetall(key) -> Dict[str, str]
    """

    type: ClassVar[str] = ""
    kind: ClassVar[str] = ""
    spec: ClassVar[Dict[str, Field]] = {}

    def __init__(self, name: str, config: Dict[str, Any], root: Path, where: str):
        self.name = name
        self.config = config  # 已按 spec 校验并补齐默认值
        self.root = root      # 相对路径的基准目录
        self.where = where

    def mget(self, keys: List[str]) -> List[Optional[str]]:
        """kv 类：批量读取，按键顺序返回，缺失为 None。

        默认逐个 get()；Redis 实现覆盖为一次 MGET（少一次往返）。
        """
        return [self.get(key) for key in keys]

    def check(self) -> None:
        """启动期自检（文件是否存在等）。不应建立网络连接。"""

    def check_dependencies(self) -> None:
        """编译使用本数据源的接口时调用：可选依赖缺失时抛 ConfigError，让错误在启动期暴露。"""

    def close(self) -> None:
        """释放资源。"""


_types: Dict[str, Type[DataSource]] = {}
D = TypeVar("D", bound=Type[DataSource])


def register_datasource(type_name: str) -> Callable[[D], D]:
    """类装饰器：登记数据源类型。新增类型与内置类型走同一机制（见 sqlite.py 的写法）。"""

    def decorator(cls: D) -> D:
        if not (isinstance(cls, type) and issubclass(cls, DataSource)) or not cls.kind:
            raise TypeError(f"@register_datasource({type_name!r}) requires a DataSource subclass with kind set")
        old = _types.get(type_name)
        if old is not None and old is not cls:
            raise ValueError(f"duplicate datasource type {type_name!r}")
        cls.type = type_name
        _types[type_name] = cls
        return cls

    return decorator


def _coerce_str_values(config: Dict[str, Any], spec: Dict[str, "Field"]) -> Dict[str, Any]:
    """datamore_lite 的 config 值全是字符串（"5000" / "true"）；数值与布尔字段自动转换。"""
    out = dict(config)
    for key, field in spec.items():
        v = out.get(key)
        if not isinstance(v, str):
            continue
        types = field.type if isinstance(field.type, tuple) else (field.type,)
        try:
            if int in types:
                out[key] = int(v)
            elif float in types:
                out[key] = float(v)
            elif bool in types and v.lower() in ("true", "false"):
                out[key] = v.lower() == "true"
        except ValueError:
            pass  # 交给 validate 报"应为整数，实际是字符串"
    return out


def create_datasource(cls: Type[DataSource], name: str, config: Dict[str, Any],
                      root: Path, where: str) -> DataSource:
    """按 spec 校验配置 → 实例化 → 自检。启动装配与测试 Mock 共用。"""
    ds = cls(name, validate(_coerce_str_values(config, cls.spec), cls.spec, where), root, where)
    ds.check()
    return ds


class DataSourceManager:
    """持有所有数据源实例，并为算子提供解析（resolve）。

    正常启动用 from_config() 按 server.yaml 实例化；算子测试框架直接传入 Mock 实例。
    允许同名数据源跨类别（对应 datamore_lite 同名 redis 与 mysql）：解析时按 (name, kind) 定位。
    """

    def __init__(self, items: Optional[List[DataSource]] = None):
        self._items: List[DataSource] = list(items or [])

    @classmethod
    def from_config(cls, entries: List[Dict[str, Any]], root: Path) -> "DataSourceManager":
        """按 server.yaml 的 dataSources（{name, type, config} 列表）实例化并自检；错误收集后一次性抛出。"""
        items: List[DataSource] = []
        errors = ErrorCollector()
        for i, entry in enumerate(entries):
            where = child(child("server.yaml", "dataSources"), i)
            with errors.collect():
                ds_cls = _types.get(entry["type"])
                if ds_cls is None:
                    raise ConfigError(f"unknown datasource type {entry['type']!r}{suggest(entry['type'], sorted(_types))}",
                                      child(where, "type"))
                items.append(create_datasource(
                    ds_cls, entry["name"], entry["config"], root, child(where, "config")))
        errors.raise_if_any()
        return cls(items)

    def resolve(self, name: Optional[str], kind: str, where: str) -> DataSource:
        """取数据源：指定 name 时按 (name, kind) 匹配；name 为空且该类别唯一时自动选中。"""
        if name:
            named = [d for d in self._items if d.name == name]
            if not named:
                raise ConfigError(f"datasource {name!r} not found{suggest(name, sorted({d.name for d in self._items}))}",
                                  where)
            matched = [d for d in named if d.kind == kind]
            if not matched:
                d = named[0]
                raise ConfigError(f"datasource {name!r} is {d.type} ({d.kind}), but {kind} is required", where)
            return matched[0]
        candidates = [d for d in self._items if d.kind == kind]
        if len(candidates) == 1:
            return candidates[0]
        names = ", ".join(d.name for d in candidates) or "无"
        raise ConfigError(f"cannot auto-select a {kind} datasource (candidates: {names}); "
                          f"set dataSource on the node config or in the group file "
                          f"({{module}}_{{group}}.yaml)", where)

    def get(self, name: str) -> Optional[DataSource]:
        """按名字取第一个匹配（仅用于存在性检查；同名跨类别时用 resolve）。"""
        return next((d for d in self._items if d.name == name), None)

    def has(self, name: str, kind: str) -> bool:
        """是否存在名为 name 且类别为 kind 的数据源。"""
        return any(d.name == name and d.kind == kind for d in self._items)

    def items(self) -> List[DataSource]:
        return list(self._items)

    def close(self) -> None:
        for ds in self._items:
            ds.close()


# 内置数据源：导入即注册（放在末尾，此时基类与装饰器已定义）
from . import http, mysql, redis, sqlite  # noqa: E402,F401

__all__ = ["DataSource", "DataSourceManager", "register_datasource", "create_datasource"]
