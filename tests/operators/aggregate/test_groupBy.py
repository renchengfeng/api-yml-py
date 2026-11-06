"""groupBy 算子测试：用例见 operator_md/aggregate/groupBy_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestgroupBy(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "groupBy"
    template = "aggregate/groupBy.yaml"
