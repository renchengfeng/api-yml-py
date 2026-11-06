"""textDiff 算子测试：用例见 operator_md/transformer/textDiff_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestTextDiff(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "textDiff"
    template = "transformer/textDiff.yaml"
