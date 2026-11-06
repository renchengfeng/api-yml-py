"""numberCast 算子测试：用例见 operator_md/transformer/numberCast_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestNumberCast(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "numberCast"
    template = "transformer/numberCast.yaml"
