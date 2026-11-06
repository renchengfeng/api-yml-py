"""fileImportTree 算子测试：用例见 operator_md/filesystem/fileImportTree_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileImportTree(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileImportTree"
    template = "external/ufs/fileImportTree.yaml"
