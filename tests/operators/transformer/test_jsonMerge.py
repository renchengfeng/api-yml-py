"""jsonMerge 算子测试：用例见 operator_md/serialization/jsonMerge_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestJsonMerge(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "jsonMerge"
    template = "transformer/jsonMerge.yaml"
