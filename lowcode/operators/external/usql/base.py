"""sqlQuery / sqlExec 的公共部分：取数据源、校验语句类型与绑定参数。

安全约束（启动期检查，见 operator_md/external/usql/ 下的手册）：
- sql 不是 dynamic 字段，写 {{ }} 会被拒绝 —— 参数只能走 :name 绑定，杜绝注入；
- 读写分离：sqlQuery 只接受 SELECT / WITH，sqlExec 只接受 INSERT / UPDATE / DELETE / REPLACE；
- 绑定参数双向核对：SQL 中的 :x 必须在 params 中提供，params 中的键也必须被 SQL 用到。
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from ....datasources.sqltext import bind_names, leading_keyword
from ....errors import ExecError
from ....spec import Field, is_template
from ...base import Operator

_SPEC = {
    "dataSource": Field(str, desc="SQL 数据源名；缺省取分组 dataSource 或唯一的 SQL 数据源"),
    "sql": Field(str, required=True, desc="SQL 文本，参数只能用 :name 绑定（不支持 {{ }}）"),
    "params": Field((dict, str), default={}, dynamic=True,
                    desc="绑定参数，值支持 {{ }}；也可整体写 \"{{ inputs }}\""),
}


class _SqlOperator(Operator):
    allowed: Tuple[str, ...] = ()

    def build(self) -> None:
        self.ds = self.env.datasource(self.config["dataSource"], "sql")
        sql = self.config["sql"]
        keyword = leading_keyword(sql)
        if keyword not in self.allowed:
            other = "sqlExec" if self.name == "sqlQuery" else "sqlQuery"
            raise self.config_error(f"{self.name} only accepts {'/'.join(self.allowed).upper()} statements, "
                                    f"got {keyword.upper() or 'empty'} (use {other} instead)", "sql")

        params = self.config["params"]
        if isinstance(params, str) and not is_template(params):
            raise self.config_error("params must be an object, or the whole \"{{ inputs }}\"", "params")
        if isinstance(params, dict):  # 整体写成 "{{ inputs }}" 时键要到运行期才知道，跳过核对
            names = bind_names(sql)
            missing = [n for n in names if n not in params]
            unused = [k for k in params if k not in names]
            if missing:
                raise self.config_error(f"bind :{missing[0]} in SQL is not provided in params", "params")
            if unused:
                raise self.config_error(f"params.{unused[0]} is not used in the SQL", "params")

    @staticmethod
    def _params(args: Dict[str, Any]) -> Dict[str, Any]:
        params = args["params"]
        if not isinstance(params, dict):
            raise ExecError(f"params 渲染结果应为对象，实际是 {type(params).__name__}")
        return params
