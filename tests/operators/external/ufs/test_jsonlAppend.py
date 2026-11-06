"""jsonlAppend 算子测试：用例见 operator_md/external/ufs/jsonlAppend_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestJsonlAppend(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "jsonlAppend"
    template = "external/ufs/jsonlAppend.yaml"
