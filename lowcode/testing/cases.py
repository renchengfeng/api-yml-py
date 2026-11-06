"""用例文件 <算子名>_input.yaml 的结构定义与加载。

文件是一个映射：用例名 → 用例。用例名即测试方法名的后缀（test_case_<用例名>），
所以只能用字母 / 数字 / 下划线；YAML 中重复的用例名会直接报错（不会静默覆盖）。

    Success:
      desc: 正常查询                      # 必填，-v 运行时显示为测试说明
      config: {single: true}             # 覆盖节点模板的 config（同名替换、新键追加、写 null 删除）
      inputs: {uid: 1}                   # 已校验的入参（模板中的 {{ inputs.x }}）
      request: {headers: {x-a: 1}}       # 请求信息（模板中的 {{ request.x }}）
      upstream: {rows: [...]}            # 上游节点输出：节点 id → 值（模板中的 {{ rows }}）
      mocks: {sqlite: {setup: ...}}      # 声明式数据源 Mock，见 mocks.py
      timeout: 5                         # 接口剩余时间（秒），默认 5
      expect: {output: ...}              # 必填，三选一：output / error / buildError
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config.loader import read_yaml
from ..errors import ConfigError
from ..spec import Field, child, validate

_CASE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_]*$")
_NODE_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_RESERVED = ("inputs", "request")

CASE_SPEC = {
    "desc": Field(str, required=True, desc="用例说明"),
    "config": Field(dict, default={}, desc="覆盖节点模板的 config"),
    "inputs": Field(dict, default={}, desc="已校验的入参"),
    "request": Field(dict, default={}, desc="请求信息"),
    "upstream": Field(dict, default={}, desc="上游节点输出：节点 id → 值"),
    "mocks": Field(dict, default={}, desc="数据源 Mock"),
    "timeout": Field((int, float), default=5, desc="接口剩余时间（秒）"),
    "expect": Field(dict, required=True, desc="期望结果：output / error / buildError 三选一"),
}
ERROR_SPEC = {
    "code": Field(int, desc="响应体业务码"),
    "status": Field(int, desc="HTTP 状态码"),
    "type": Field(str, desc="异常类名，如 ExecError / BizError / UpstreamError"),
    "msg": Field(str, desc="错误信息应包含的片段"),
}
_EXPECT_KEYS = ("output", "error", "buildError")


@dataclass
class Expect:
    kind: str                     # output / error / buildError
    output: Any = None            # kind=output：期望输出（严格比较，见 assertion.py）
    error: Optional[Dict[str, Any]] = None   # kind=error：运行期错误的各字段
    build_error: str = ""         # kind=buildError：构建期错误信息应包含的片段


@dataclass
class InputCase:
    name: str
    desc: str
    config: Dict[str, Any]
    inputs: Dict[str, Any]
    request: Dict[str, Any]
    upstream: Dict[str, Any]
    mocks: Dict[str, Any]
    timeout: float
    expect: Expect
    where: str


def load_cases(path: Path, where: str) -> List[InputCase]:
    """加载并校验用例文件，按文件中的书写顺序返回。

    以 _ 开头的顶层键不是用例，用来放 YAML 锚点（如多个用例共享的 Mock 数据）：
        _db: &db {sqlite: {setup: ...}}
        Success: {desc: ..., mocks: *db, expect: ...}
    """
    raw = read_yaml(path, where)
    if not isinstance(raw, dict):
        raise ConfigError("case file must be a mapping: case name -> case", where)
    cases = [_parse_case(str(name), body, child(where, str(name)))
             for name, body in raw.items() if not str(name).startswith("_")]
    if not cases:
        raise ConfigError("no cases found in case file", where)
    return cases


def _parse_case(name: str, body: Any, where: str) -> InputCase:
    if not _CASE_NAME.match(name):
        raise ConfigError(f"invalid case name {name!r}: letters/digits/underscore only", where)
    c = validate(body, CASE_SPEC, where)
    for nid in c["upstream"]:
        if not isinstance(nid, str) or not _NODE_ID.match(nid) or nid in _RESERVED:
            raise ConfigError(f"invalid upstream node id {nid!r} (must be an identifier, not inputs/request)",
                              child(where, "upstream"))
    return InputCase(name=name, desc=c["desc"], config=c["config"], inputs=c["inputs"],
                     request=c["request"], upstream=c["upstream"], mocks=c["mocks"],
                     timeout=c["timeout"], expect=_parse_expect(c["expect"], child(where, "expect")),
                     where=where)


def _parse_expect(raw: Dict[str, Any], where: str) -> Expect:
    # 不能直接用 validate：output 的期望值可能恰好是 null，而 validate 会把 null 当作"没写"
    keys = [k for k in raw if k in _EXPECT_KEYS]
    unknown = [k for k in raw if k not in _EXPECT_KEYS]
    if unknown:
        raise ConfigError(f"unknown field {unknown[0]!r} (available: {', '.join(_EXPECT_KEYS)})", where)
    if len(keys) != 1:
        raise ConfigError("exactly one of output / error / buildError is required", where)
    kind = keys[0]
    if kind == "output":
        return Expect(kind, output=raw["output"])
    if kind == "error":
        err = validate(raw["error"], ERROR_SPEC, child(where, "error"))
        if all(v is None for v in err.values()):
            raise ConfigError("error requires at least one of code / status / type / msg", child(where, "error"))
        return Expect(kind, error=err)
    if not isinstance(raw["buildError"], str) or not raw["buildError"]:
        raise ConfigError("buildError must be a non-empty string (a fragment of the expected message)", child(where, "buildError"))
    return Expect(kind, build_error=raw["buildError"])
