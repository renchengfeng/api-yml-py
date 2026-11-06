"""httpRequest 算子测试：用例见 operator_md/external/uhttp/httpRequest_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestHttpRequest(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "httpRequest"
    template = "external/uhttp/httpRequest.yaml"
