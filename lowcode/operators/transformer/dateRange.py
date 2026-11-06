"""dateRange：按起止日期生成日期列表。手册与用例见 operator_md/transformer/dateRange.md。"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from ...errors import ParamError
from ...spec import Field
from ..base import Operator
from ..registry import register


@register("dateRange", category="transformer")
class DateRange(Operator):
    """按起止日期生成日期列表（含首尾），便于下游按天展开。"""

    spec = {
        "start": Field(str, required=True, dynamic=True, desc="起始日期（含），格式由 format 决定"),
        "end": Field(str, required=True, dynamic=True, desc="结束日期（含），格式由 format 决定"),
        "format": Field(str, default="%Y%m%d", desc="日期格式（strftime / strptime），如 %Y%m%d、%Y-%m-%d"),
        "limit": Field(int, default=366, desc="区间最大天数；超过直接报 400，避免下游 fan-out 打爆"),
    }

    def build(self) -> None:
        fmt = self.config["format"]
        try:
            datetime.strptime(datetime(2001, 2, 3).strftime(fmt), fmt)
        except ValueError as e:
            raise self.config_error(f"invalid date format {fmt!r}: {e}", "format")
        if self.config["limit"] < 1:
            raise self.config_error("limit must be >= 1", "limit")

    def execute(self, ctx: Any, args: Dict[str, Any]) -> List[str]:
        fmt = self.config["format"]
        try:
            start = datetime.strptime(str(args["start"]), fmt).date()
            end = datetime.strptime(str(args["end"]), fmt).date()
        except ValueError as e:
            raise ParamError(f"invalid date (format {fmt!r}): {e}") from None
        if end < start:
            raise ParamError(f"start {args['start']!r} is after end {args['end']!r}")
        days = (end - start).days + 1
        limit = self.config["limit"]
        if days > limit:
            raise ParamError(f"date range too large: {days} days (limit {limit})")
        return [(start + timedelta(days=i)).strftime(fmt) for i in range(days)]
