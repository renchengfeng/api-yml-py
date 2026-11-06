"""fileWrite 算子测试：用例见 operator_md/filesystem/fileWrite_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileWrite(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileWrite"
    template = "external/ufs/fileWrite.yaml"
