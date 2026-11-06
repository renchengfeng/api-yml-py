"""fileExists 算子测试：用例见 operator_md/filesystem/fileExists_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileExists(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileExists"
    template = "external/ufs/fileExists.yaml"
