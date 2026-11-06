"""算子测试框架：节点模板 + YAML 用例 + 声明式 Mock，用例驱动地测试单个算子。

    from lowcode.testing import OperatorTestSuite

使用说明见 docs/TESTING.md。
"""
from .assertion import first_diff
from .cases import Expect, InputCase, load_cases
from .mocks import MockRedis, build_mocks
from .suite import OperatorTestSuite, run_case

__all__ = ["OperatorTestSuite", "run_case", "load_cases", "InputCase", "Expect",
           "build_mocks", "MockRedis", "first_diff"]
