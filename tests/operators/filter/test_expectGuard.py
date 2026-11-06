"""expectGuard 算子测试：用例见 operator_md/filter/expectGuard_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestExpectExpectGuard(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "expectGuard"
    template = "filter/expectGuard.yaml"
