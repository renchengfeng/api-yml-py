"""hashTree 算子测试：用例见 operator_md/filesystem/hashTree_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestHashTree(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "hashTree"
    template = "external/ufs/hashTree.yaml"
