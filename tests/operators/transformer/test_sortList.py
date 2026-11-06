"""sortList 算子测试：用例见 operator_md/collection/sortList_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestSortList(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "sortList"
    template = "transformer/sortList.yaml"
