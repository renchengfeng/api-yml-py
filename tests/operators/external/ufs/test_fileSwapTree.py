"""fileSwapTree 算子测试：用例见 operator_md/filesystem/fileSwapTree_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileSwapTree(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileSwapTree"
    template = "external/ufs/fileSwapTree.yaml"
