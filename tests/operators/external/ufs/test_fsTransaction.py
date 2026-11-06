"""fsTransaction 算子测试：用例见 operator_md/filesystem/fsTransaction_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFsTransaction(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fsTransaction"
    template = "external/ufs/fsTransaction.yaml"
