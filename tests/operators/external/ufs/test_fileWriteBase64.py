"""fileWriteBase64 算子测试：用例见 operator_md/filesystem/fileWriteBase64_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileWriteBase64(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileWriteBase64"
    template = "external/ufs/fileWriteBase64.yaml"
