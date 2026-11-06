"""jsonStringify 算子测试：用例见 operator_md/serialization/jsonStringify_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestJsonStringify(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "jsonStringify"
    template = "transformer/jsonStringify.yaml"
