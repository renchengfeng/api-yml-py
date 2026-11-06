"""hash 算子测试：用例见 operator_md/encoding/hash_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestHash(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "hash"
    template = "transformer/hash.yaml"
