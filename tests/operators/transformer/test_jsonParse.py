"""jsonParse 算子测试：用例见 operator_md/serialization/jsonParse_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestJsonParse(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "jsonParse"
    template = "transformer/jsonParse.yaml"
