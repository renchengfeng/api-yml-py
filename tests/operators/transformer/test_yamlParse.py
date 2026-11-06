"""yamlParse 算子测试：用例见 operator_md/serialization/yamlParse_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestYamlParse(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "yamlParse"
    template = "transformer/yamlParse.yaml"
