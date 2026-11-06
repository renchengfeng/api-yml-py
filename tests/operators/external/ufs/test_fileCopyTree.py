"""fileCopyTree 算子测试：用例见 operator_md/filesystem/fileCopyTree_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileCopyTree(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileCopyTree"
    template = "external/ufs/fileCopyTree.yaml"
