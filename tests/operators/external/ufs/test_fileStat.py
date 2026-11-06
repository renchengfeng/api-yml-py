"""fileStat 算子测试：用例见 operator_md/filesystem/fileStat_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileStat(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileStat"
    template = "external/ufs/fileStat.yaml"
