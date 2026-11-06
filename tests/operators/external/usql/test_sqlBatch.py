"""sqlBatch 算子测试：用例见 operator_md/external/sqlBatch_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestSqlBatch(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "sqlBatch"
    template = "external/usql/sqlBatch.yaml"
