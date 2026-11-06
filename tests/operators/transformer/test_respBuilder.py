"""respBuilder 算子测试：用例见 operator_md/transformer/respBuilder_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestRespBuilder(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "respBuilder"
    template = "transformer/respBuilder.yaml"
