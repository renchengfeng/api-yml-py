"""fieldPicker 算子测试：用例见 operator_md/selector/fieldPicker_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestfieldPicker(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fieldPicker"
    template = "selector/fieldPicker.yaml"
