"""ruleCheck 算子测试：用例见 operator_md/validate/ruleCheck_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestRuleCheck(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "ruleCheck"
    template = "validate/ruleCheck.yaml"
