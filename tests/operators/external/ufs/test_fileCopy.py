"""fileCopy 算子测试：用例见 operator_md/filesystem/fileCopy_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileCopy(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileCopy"
    template = "external/ufs/fileCopy.yaml"
