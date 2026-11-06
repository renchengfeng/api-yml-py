"""rowFilter 算子测试：用例见 operator_md/transformer/rowFilter_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestRowFilter(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "rowFilter"
    template = "transformer/rowFilter.yaml"
