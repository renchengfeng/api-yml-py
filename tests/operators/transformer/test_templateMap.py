"""templateMap 算子测试：用例见 operator_md/transformer/templateMap_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestTemplateMap(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "templateMap"
    template = "transformer/templateMap.yaml"
