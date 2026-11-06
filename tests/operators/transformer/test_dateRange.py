"""dateRange 算子测试：用例见 operator_md/transformer/dateRange_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestDateRange(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "dateRange"
    template = "transformer/dateRange.yaml"
