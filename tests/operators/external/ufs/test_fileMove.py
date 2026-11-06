"""fileMove 算子测试：用例见 operator_md/filesystem/fileMove_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileMove(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileMove"
    template = "external/ufs/fileMove.yaml"
