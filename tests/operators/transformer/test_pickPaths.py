"""pickPaths 算子测试：用例见 operator_md/collection/pickPaths_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestPickPaths(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "pickPaths"
    template = "transformer/pickPaths.yaml"
