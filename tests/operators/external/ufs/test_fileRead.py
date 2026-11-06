"""fileRead 算子测试：用例见 operator_md/filesystem/fileRead_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileRead(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileRead"
    template = "external/ufs/fileRead.yaml"
