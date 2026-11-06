"""expectGuard：断言，条件不满足即中止接口。手册与用例见 operator_md/filter/expectGuard.md。"""
from __future__ import annotations

from typing import Any, Dict

from ...errors import BizError
from ...spec import Field
from ..base import Operator
from ..registry import register


@register("expectGuard", category="filter")
class ExpectGuard(Operator):
    """断言：expect 为假时中止接口，返回指定 code / msg（如查不到数据时返回 404）。"""

    spec = {
        "expect": Field(object, required=True, dynamic=True, desc="期望为真的条件，如 \"{{ user }}\""),
        "code": Field(int, default=400, desc="400~599 同时作为 HTTP 状态码，否则 HTTP 200 + 业务码"),
        "msg": Field(str, default="校验未通过", dynamic=True),
    }

    def build(self) -> None:
        if self.config["code"] == 0:
            raise self.config_error("code must not be 0 (0 means success)", "code")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        if not args["expect"]:
            raise BizError(args["msg"], args["code"])
        return True
