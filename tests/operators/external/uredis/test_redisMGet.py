"""redisMGet 算子测试：用例见 operator_md/external/uredis/redisMGet_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestRedisMGet(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "redisMGet"
    template = "external/uredis/redisMGet.yaml"
