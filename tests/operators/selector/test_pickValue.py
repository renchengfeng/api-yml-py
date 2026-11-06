"""branch 算子测试：用例见 operator_md/selector/pickValue_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestPickValue(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "pickValue"
    template = "selector/pickValue.yaml"
