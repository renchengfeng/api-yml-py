"""fileDeleteTree 算子测试：用例见 operator_md/filesystem/fileDeleteTree_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileDeleteTree(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileDeleteTree"
    template = "external/ufs/fileDeleteTree.yaml"
