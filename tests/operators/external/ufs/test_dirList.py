"""dirList 算子测试：用例见 operator_md/filesystem/dirList_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestDirList(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "dirList"
    template = "external/ufs/dirList.yaml"
