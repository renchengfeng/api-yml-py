"""listAgg 算子测试：用例见 operator_md/aggregate/listAgg_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestlistAgg(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "listAgg"
    template = "aggregate/listAgg.yaml"
