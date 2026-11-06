"""frontmatterParse 算子测试：用例见 operator_md/document/frontmatterParse_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFrontmatterParse(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "frontmatterParse"
    template = "transformer/frontmatterParse.yaml"
