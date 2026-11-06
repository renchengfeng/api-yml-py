"""zipExtract 算子测试：用例见 operator_md/archive/zipExtract_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestZipExtract(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "zipExtract"
    template = "external/ufs/zipExtract.yaml"
