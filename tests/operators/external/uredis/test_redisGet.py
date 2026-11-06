"""redisGet 算子测试：用例见 operator_md/external/uredis/redisGet_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestRedisGet(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "redisGet"
    template = "external/uredis/redisGet.yaml"
