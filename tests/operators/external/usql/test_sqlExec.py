"""sqlExec 算子测试：用例见 operator_md/external/usql/sqlExec_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestSqlExec(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "sqlExec"
    template = "external/usql/sqlExec.yaml"
