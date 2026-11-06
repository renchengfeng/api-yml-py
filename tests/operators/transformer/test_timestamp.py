"""timestamp 算子测试：用例见 operator_md/transformer/timestamp_input.yaml。"""
from lowcode.testing import OperatorTestSuite
from tests.operators import MD_ROOT
class TestTimestamp(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "timestamp"
    template = "transformer/timestamp.yaml"
