"""graphCheck 算子测试：用例见 operator_md/validate/graphCheck_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestGraphCheck(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "graphCheck"
    template = "validate/graphCheck.yaml"
