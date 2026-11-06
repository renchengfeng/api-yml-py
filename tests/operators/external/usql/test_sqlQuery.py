"""sqlQuery 算子测试：用例见 operator_md/external/usql/sqlQuery_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestSqlQuery(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "sqlQuery"
    template = "external/usql/sqlQuery.yaml"
