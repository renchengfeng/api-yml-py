"""SQL 文本工具：识别 :name 绑定参数（跳过引号内的字面量）。

供 sqlQuery / sqlExec 在启动期核对绑定参数，以及 mysql 数据源把 :name 转成 %(name)s。
"""
from __future__ import annotations

import re
from typing import List

# 单引号字符串（'' 为转义）、双引号标识符、-- 行注释、/* */ 块注释：这些区域里的 :x 不是绑定参数
_SKIP = re.compile(r"'(?:[^']|'')*'|\"[^\"]*\"|--[^\n]*|/\*.*?\*/", re.S)
_BIND = re.compile(r"(?<![:\w]):([A-Za-z_]\w*)")  # 排除 ::type 强转与 10:30 这类时间
_LEADING = re.compile(r"^\s*(?:(?:--[^\n]*\n)|(?:/\*.*?\*/))*\s*(\w+)", re.S)


def _segments(sql: str):
    """把 SQL 切成 (是否可替换, 文本) 片段。"""
    pos = 0
    for m in _SKIP.finditer(sql):
        yield True, sql[pos:m.start()]
        yield False, m.group(0)
        pos = m.end()
    yield True, sql[pos:]


def bind_names(sql: str) -> List[str]:
    """SQL 中出现的绑定参数名（去重，保持出现顺序）。"""
    names: List[str] = []
    for live, text in _segments(sql):
        if live:
            names.extend(n for n in _BIND.findall(text) if n not in names)
    return names


def to_pyformat(sql: str) -> str:
    """:name → %(name)s，并把字面量 % 转义成 %%（pymysql 等 DB-API 驱动使用 pyformat）。"""
    out = []
    for live, text in _segments(sql):
        text = text.replace("%", "%%")
        out.append(_BIND.sub(r"%(\1)s", text) if live else text)
    return "".join(out)


def leading_keyword(sql: str) -> str:
    """SQL 的首个关键字（小写），跳过前导注释。"""
    m = _LEADING.match(sql)
    return m.group(1).lower() if m else ""
