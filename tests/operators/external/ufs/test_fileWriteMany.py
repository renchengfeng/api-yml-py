"""fileWriteMany 算子测试：用例见 operator_md/filesystem/fileWriteMany_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileWriteMany(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileWriteMany"
    template = "external/ufs/fileWriteMany.yaml"
