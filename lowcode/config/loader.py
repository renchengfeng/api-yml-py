"""配置加载：扫描目录 → 解析 YAML → 按 *_SPEC 校验 → 生成 *Def。

四层与文件约定（`-c` 指向的目录，一层一个文件）：
    <root>/server.yaml                    第一层 Server：公共配置（唯一，必需）
    <root>/{module}_{group}.yaml          第二层 Group：分组配置（可选，全部字段可选）
    <root>/{module}_{group}_{api}.yaml    第三层 API：一个文件一个接口
    文件内的 graph[]                      第四层 算子节点

文件名三段同时决定接口的 path 前缀，接口文件里必须显式声明完整 path：
    path: /{module}/{group}/{api}
启动期会校验 path 与文件名一致（不允许文件名与路由各说一套）。
因此模块名、分组名、接口名都不能包含下划线（下划线是分隔符）。
以 `_` 或 `.` 开头的文件、非 YAML 文件会被忽略（可用来临时下线）。
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from yaml.constructor import ConstructorError
from ..errors import ConfigError, ErrorCollector
from ..spec import child, validate
from .models import (API_SPEC, DATASOURCE_ENTRY_SPEC, GROUP_SPEC, INPUT_SPEC, NODE_SPEC,
                     OUTPUT_SPEC, SERVER_FILE_SPEC, SERVER_SPEC, TYPE_ALIASES, ApiDef, GroupDef,
                     InputDef, NodeDef, OutputDef, ServerDef)

SERVER_FILE = "server.yaml"
_YAML_SUFFIX = (".yaml", ".yml")
_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*\Z")
_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?}")
_LAYOUT_HINT = ("file name must be {module}_{group}_{api}.yaml (api) "
                "or {module}_{group}.yaml (group)")


def load_config(root: Union[str, Path], errors: Optional[ErrorCollector] = None) -> ServerDef:
    """加载配置目录。传入 errors 时错误追加、出错文件跳过（供 runtime 把结构/语义错误一次列全）。"""
    root = Path(root).resolve()
    server_path = root / SERVER_FILE
    if not server_path.is_file():
        raise ConfigError(f"config file not found: {SERVER_FILE}", str(root))

    raw = _expand_env(read_yaml(server_path, SERVER_FILE), SERVER_FILE)
    top = validate(raw, SERVER_FILE_SPEC, SERVER_FILE)
    srv = validate(top["server"], SERVER_SPEC, child(SERVER_FILE, "server"))
    _check_datasources(top["dataSources"])

    collector = errors if errors is not None else ErrorCollector()
    groups = _scan(root, collector)
    if errors is None:
        collector.raise_if_any()
    if not collector.errors and not any(g.apis for g in groups):
        raise ConfigError(f"no apis found: add {_LAYOUT_HINT} under the config directory", str(root))

    return ServerDef(
        name=top["name"], host=srv["host"], port=srv["port"], prefix=srv["prefix"],
        timeout=srv["timeout"], parallel=srv["parallel"], workers=srv["workers"],
        debug=srv["debug"], meta=srv["meta"], log_level=srv["logLevel"],
        data_sources=top["dataSources"], root=root, groups=groups,
    )


def _scan(root: Path, errors: ErrorCollector) -> List[GroupDef]:
    """扫一遍目录：文件名两段是分组配置，三段是接口；分组按 module/group 归档。"""
    group_cfg: Dict[Tuple[str, str], Tuple[str, Dict[str, Any]]] = {}
    api_files: List[Tuple[str, str, str, Path, str]] = []
    for f in sorted(root.iterdir()):
        if not f.is_file() or f.name.startswith(("_", ".")) or f.suffix.lower() not in _YAML_SUFFIX:
            continue
        if f.name == SERVER_FILE:  # 公共配置单独处理，不参与分组扫描
            continue
        where = f.relative_to(root).as_posix()
        with errors.collect():  # 单个文件出错不影响其它文件的校验
            module, group, api = _parse_filename(f.stem, where)
            if api is None:
                if (module, group) in group_cfg:
                    raise ConfigError(f"duplicate group config (already in {group_cfg[(module, group)][0]})", where)
                group_cfg[(module, group)] = (where, validate(read_yaml(f, where), GROUP_SPEC, where))
            else:
                api_files.append((module, group, api, f, where))

    keys = sorted({(m, g) for m, g in group_cfg} | {(m, g) for m, g, *_ in api_files})
    groups = []
    for module, group in keys:
        _, cfg = group_cfg.get((module, group), (f"{module}_{group}.yaml", {}))
        groups.append(GroupDef(
            module=module, group=group,
            name=cfg.get("name") or group, desc=cfg.get("desc", ""),
            data_source=cfg.get("dataSource"), timeout=cfg.get("timeout"),
        ))

    index = {g.key: g for g in groups}
    for module, group, api, f, where in sorted(api_files, key=lambda t: (t[0], t[1], t[2])):
        with errors.collect():
            index[f"{module}_{group}"].apis.append(_load_api(f, where, module, group, api))
    return groups


def _parse_filename(stem: str, where: str) -> Tuple[str, str, Optional[str]]:
    """文件名 → (模块, 分组, 接口)。2 段是分组配置，3 段是接口，接口名为 None 表示分组配置。"""
    parts = stem.split("_")
    if len(parts) not in (2, 3):
        raise ConfigError(f"{_LAYOUT_HINT}; got {stem!r} with {len(parts)} segments", where)
    module, group = parts[0], parts[1]
    _check_segment(module, "module", where)
    _check_segment(group, "group", where)
    if len(parts) == 2:
        return module, group, None
    _check_segment(parts[2], "api", where)
    return module, group, parts[2]


def _check_segment(value: str, label: str, where: str) -> None:
    if not _SEGMENT.match(value):
        raise ConfigError(f"invalid {label} name {value!r}: must start with a letter or a digit and "
                          "contain only letters / digits / dashes "
                          "(underscore is the file name separator)", where)


def _check_path(value: str, module: str, group: str, slug: str, where: str) -> str:
    """path 是接口的完整路径，前三段必须与文件名一致（文件名与路由不允许各说一套）。"""
    path = value.strip().rstrip("/")
    if not path.startswith("/"):
        raise ConfigError(f"path must start with / and be the full route, e.g. /{module}/{group}/{slug}", where)
    expected = f"/{module}/{group}/{slug}"
    if path != expected and not path.startswith(expected + "/"):
        raise ConfigError(f"path {value!r} does not match the file name: expected {expected!r} "
                          f"or {expected}/... (path params / extra segments)", where)
    return path


def _load_api(f: Path, where: str, module: str, group: str, slug: str) -> ApiDef:
    raw = read_yaml(f, where)
    if isinstance(raw, dict) and isinstance(raw.get("method"), str):
        raw["method"] = raw["method"].upper()  # 方法名不区分大小写
    a = validate(raw, API_SPEC, where)
    path = _check_path(a["path"], module, group, slug, child(where, "path"))

    inputs_at, graph_at = child(where, "inputs"), child(where, "graph")
    inputs = [_load_input(item, child(inputs_at, i)) for i, item in enumerate(a["inputs"])]
    outputs = _load_outputs(a["outputs"], child(where, "outputs"))
    graph = [load_node(item, child(graph_at, i)) for i, item in enumerate(a["graph"])]
    if not graph:
        raise ConfigError("at least one node is required", graph_at)

    return ApiDef(
        name=a["name"], method=a["method"], path=path, desc=a["desc"],
        timeout=a["timeout"], inputs=inputs, outputs=outputs, graph=graph, slug=slug, where=where,
    )


def _load_outputs(items: Any, where: str) -> List[OutputDef]:
    """解析 outputs 声明；字段名重复直接报错。"""
    out: List[OutputDef] = []
    seen = set()
    for i, item in enumerate(items):
        d = validate(item, OUTPUT_SPEC, child(where, i))
        if d["name"] in seen:
            raise ConfigError(f"duplicate output field {d['name']!r}", child(where, i))
        seen.add(d["name"])
        out.append(OutputDef(where=child(where, i), **d))
    return out


def _load_input(item: Any, where: str) -> InputDef:
    d = validate(item, INPUT_SPEC, where)
    d["type"] = TYPE_ALIASES.get(d["type"], d["type"])
    return InputDef(where=where, **d)


def load_node(item: Any, where: str) -> NodeDef:
    d = validate(item, NODE_SPEC, where)
    depends = d["depends"]
    if depends is not None:
        for i, dep in enumerate(depends):
            if isinstance(dep, bool) or not isinstance(dep, (str, int)):
                raise ConfigError(f"node id must be a string, got {dep!r}", child(child(where, "depends"), i))
        depends = [str(dep) for dep in depends]
    return NodeDef(
        name=d["name"], id=None if d["id"] is None else str(d["id"]),
        depends=depends, config=d["config"], desc=d["desc"], where=where,
    )


def _check_datasources(entries: Any) -> None:
    """只检查条目形状与重名（同名同类别视为重复；具体参数由数据源层校验）。"""
    seen = set()
    for i, raw in enumerate(entries):
        where = child(child(SERVER_FILE, "dataSources"), i)
        e = validate(raw, DATASOURCE_ENTRY_SPEC, where)
        key = (e["name"], e["type"])
        if key in seen:
            raise ConfigError(f"duplicate datasource {e['name']!r} ({e['type']})", where)
        seen.add(key)


class _UniqueKeyLoader(yaml.SafeLoader):
    """拒绝重复键（PyYAML 默认静默后者覆盖前者，datamore 的配置就踩过这个坑）。"""

    def construct_mapping(self, node, deep=False):  # noqa: D401  覆盖父类方法
        seen = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicated = key in seen
            except TypeError:  # 不可哈希的键交给父类报错
                break
            if duplicated:
                raise ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def read_yaml(path: Path, where: str) -> Any:
    """读取 YAML；语法错误转成带行号的 ConfigError；空文件返回 {}。"""
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.load(fh, Loader=_UniqueKeyLoader)  # noqa: S506  基于 SafeLoader
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        line = f" (line {mark.line + 1})" if mark else ""
        raise ConfigError(f"YAML parse error{line}: {getattr(e, 'problem', None) or e}", where) from None
    return {} if data is None else data


def _expand_env(value: Any, where: str) -> Any:
    """展开 ${VAR} / ${VAR:-默认}；整串只有一个引用时还原类型（"${PORT}" → int）。"""
    if isinstance(value, dict):
        return {k: _expand_env(v, child(where, k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v, child(where, i)) for i, v in enumerate(value)]
    if not isinstance(value, str) or "${" not in value:
        return value

    def replace(m: "re.Match[str]") -> str:
        name, default = m.group(1), m.group(2)
        if name in os.environ:
            return os.environ[name]
        if default is not None:
            return default
        raise ConfigError(f"environment variable {name} is not set (use ${{{name}:-default}})", where)

    text = _ENV_REF.sub(replace, value)
    if _ENV_REF.fullmatch(value.strip()):
        try:
            scalar = yaml.safe_load(text)
        except yaml.YAMLError:
            return text
        if isinstance(scalar, (bool, int, float)):
            return scalar
    return text
