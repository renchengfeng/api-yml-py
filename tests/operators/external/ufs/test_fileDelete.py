"""fileDelete 算子测试：用例见 operator_md/filesystem/fileDelete_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileDelete(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileDelete"
    template = "external/ufs/fileDelete.yaml"
