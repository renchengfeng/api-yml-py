"""fileReadMany 算子测试：用例见 operator_md/filesystem/fileReadMany_input.yaml。"""
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT


class TestFileReadMany(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "fileReadMany"
    template = "external/ufs/fileReadMany.yaml"
