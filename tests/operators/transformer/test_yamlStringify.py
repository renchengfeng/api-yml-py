"""yamlStringify 算子测试：用例见 operator_md/serialization/yamlStringify_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestYamlStringify(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "yamlStringify"
    template = "transformer/yamlStringify.yaml"
