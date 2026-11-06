"""listAppend 算子测试：用例见 operator_md/collection/listAppend_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestListAppend(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "listAppend"
    template = "transformer/listAppend.yaml"
