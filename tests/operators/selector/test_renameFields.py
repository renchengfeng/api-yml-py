"""renameFields 算子测试：用例见 operator_md/selector/renameFields_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestRenameFields(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "renameFields"
    template = "selector/renameFields.yaml"
