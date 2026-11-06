"""uuid 算子测试：用例见 operator_md/transformer/uuid_input.yaml。"""
from lowcode.testing import OperatorTestSuite
from tests.operators import MD_ROOT
class TestUuid(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "uuid"
    template = "transformer/uuid.yaml"
