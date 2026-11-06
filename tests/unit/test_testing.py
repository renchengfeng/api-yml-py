"""算子测试框架（lowcode.testing）自身的测试：确认它能抓住各类错误，而不是只会亮绿灯。"""
import textwrap
import unittest
from pathlib import Path

import lowcode.operators  # noqa: F401  导入即注册内置算子
from lowcode.config.loader import load_node
from lowcode.errors import ConfigError
from lowcode.testing import OperatorTestSuite, first_diff, load_cases, run_case

from ..support import TempConfCase


class FirstDiffTest(unittest.TestCase):
    def test_equal(self):
        self.assertIsNone(first_diff({"a": [1, 2.0, None, "x"]}, {"a": [1.0, 2, None, "x"]}))  # int/float 同为数字
        self.assertIsNone(first_diff({"a": 1, "b": 2}, {"b": 2, "a": 1}))                      # 不比较键顺序
        self.assertIsNone(first_diff((1, 2), [1, 2]))                                          # tuple 视同列表

    def test_strict_categories(self):
        cases = [(True, 1, "expected 1 (number), got True (boolean)"),
                 ("1", 1, "got '1' (string)"),
                 (None, [], "expected [] (list), got None (null)")]
        for actual, expected, msg in cases:
            with self.subTest(actual=actual):
                self.assertIn(msg, first_diff(actual, expected))

    def test_path_of_first_difference(self):
        diff = first_diff({"list": [{"id": 1}, {"id": "2"}]}, {"list": [{"id": 1}, {"id": 2}]})
        self.assertTrue(diff.startswith("output.list[1].id:"))
        self.assertIn("missing keys ['b'], extra keys ['c']", first_diff({"a": 1, "c": 1}, {"a": 1, "b": 1}))
        self.assertIn("expected 2 items, got 1", first_diff([1], [1, 2]))


class _Base(TempConfCase):
    """把 YAML 写进临时文件后用框架加载；run() 用 self 作为 TestCase 执行用例。"""

    def cases(self, text: str):
        path = self.root / "op_input.yaml"
        path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")
        return load_cases(path, "op_input.yaml")

    def run_one(self, template: dict, case_yaml: str) -> None:
        run_case(self, load_node(template, "tpl.yaml"), self.cases(case_yaml)[0])

    def assert_case_fails(self, template: dict, case_yaml: str, msg: str) -> None:
        with self.assertRaises(AssertionError) as cm:
            self.run_one(template, case_yaml)
        self.assertIn(msg, str(cm.exception))


RESP = {"name": "respBuilder", "config": {"data": "{{ rows }}"}}


class CaseLoadingTest(_Base):
    def test_valid_cases_keep_order_and_skip_anchor_keys(self):
        cases = self.cases("""
            _shared: &up {rows: [1]}
            B: {desc: b, upstream: *up, expect: {output: [1]}}
            A: {desc: a, expect: {output: null}}
        """)
        self.assertEqual([c.name for c in cases], ["B", "A"])
        self.assertEqual(cases[0].upstream, {"rows": [1]})
        self.assertIsNone(cases[1].expect.output)  # 期望输出恰好是 null 也能表达

    def test_invalid_cases(self):
        bad = {
            "A: {desc: a, expect: {output: 1}, inptus: {}}": "did you mean 'inputs'?",
            "A: {expect: {output: 1}}": "desc: missing required field",
            "A: {desc: a, expect: {}}": "exactly one of output / error / buildError",
            "A: {desc: a, expect: {output: 1, buildError: x}}": "exactly one of output / error / buildError",
            "A: {desc: a, expect: {outputs: 1}}": "unknown field 'outputs'",
            "A: {desc: a, expect: {error: {}}}": "requires at least one of",
            "A: {desc: a, expect: {error: {cod: 1}}}": "did you mean 'code'?",
            "a-b: {desc: a, expect: {output: 1}}": "letters/digits/underscore only",
            "A: {desc: a, upstream: {inputs: 1}, expect: {output: 1}}": "invalid upstream node id 'inputs'",
            "A: {desc: a, expect: {output: 1}}\nA: {desc: b, expect: {output: 2}}": "duplicate key 'A'",
            "_only_anchor: 1": "no cases found in case file",
        }
        for text, msg in bad.items():
            with self.subTest(msg=msg), self.assertRaises(ConfigError) as cm:
                self.cases(text)
            self.assertIn(msg, str(cm.exception))


class RunCaseTest(_Base):
    def test_pass(self):
        self.run_one(RESP, "A: {desc: a, upstream: {rows: [1]}, expect: {output: [1]}}")

    def test_wrong_output_is_reported_with_actual_yaml(self):
        self.assert_case_fails(RESP, "A: {desc: a, upstream: {rows: [1]}, expect: {output: [2]}}",
                               "output[0]: expected 2, got 1")
        self.assert_case_fails(RESP, "A: {desc: a, upstream: {rows: [1]}, expect: {output: [2]}}",
                               "实际输出：\n[1]")  # 可直接粘贴回用例文件

    def test_success_vs_error_mismatch(self):
        self.assert_case_fails(RESP, "A: {desc: a, upstream: {rows: 1}, expect: {error: {code: 500}}}",
                               "expected an error, but it succeeded")
        tpl = {"name": "respBuilder", "config": {"data": "{{ rows.nope }}"}}
        self.assert_case_fails(tpl, "A: {desc: a, upstream: {rows: {}}, expect: {output: 1}}",
                               "expected success, got ExecError(code=500)")

    def test_error_fields(self):
        tpl = {"name": "expectGuard", "config": {"expect": False, "code": 404, "msg": "nf"}}
        self.run_one(tpl, "A: {desc: a, expect: {error: {type: BizError, code: 404, status: 404, msg: nf}}}")
        self.assert_case_fails(tpl, "A: {desc: a, expect: {error: {code: 400}}}", "error.code expected 400, got 404")
        self.assert_case_fails(tpl, "A: {desc: a, expect: {error: {type: ExecError}}}", "got 'BizError'")

    def test_build_error(self):
        bad = {"name": "respBuilder", "config": {"data": "{{ nope }}"}}
        self.run_one(bad, "A: {desc: a, expect: {buildError: unknown variable}}")
        self.assert_case_fails(bad, "A: {desc: a, expect: {buildError: 别的错误}}", "build error does not contain '别的错误'")
        self.assert_case_fails(RESP, "A: {desc: a, upstream: {rows: 1}, expect: {buildError: x}}",
                               "expected build error containing 'x', but build succeeded")
        self.assert_case_fails(bad, "A: {desc: a, expect: {output: 1}}", "build failed")

    def test_contract_violations_are_detected(self):
        self.assert_case_fails({"name": "badMutator", "config": {"data": "{{ rows }}"}},
                               "A: {desc: a, upstream: {rows: [1]}, expect: {output: [1, oops]}}",
                               "operator mutated upstream")
        self.assert_case_fails({"name": "badConfigMutator", "config": {"tags": ["a"]}},
                               "A: {desc: a, expect: {output: [a, oops]}}",
                               "operator mutated config")

    def test_case_config_overrides_template(self):
        tpl = {"name": "respBuilder", "config": {"data": {"a": 1}}}
        self.run_one(tpl, "A: {desc: a, config: {data: {b: 2}}, expect: {output: {b: 2}}}")

    def test_mock_errors(self):
        cases = {
            "A: {desc: a, mocks: {mongo: {}}, expect: {output: 1}}": "unknown mock type 'mongo'",
            "A: {desc: a, mocks: {http: {routes: {/x: {}}}}, expect: {output: 1}}": "'METHOD /path'",
            "A: {desc: a, mocks: {http: {routes: {GET /x: {json: 1, text: a}}}}, expect: {output: 1}}":
                "only one of json / text may be set",
            "A: {desc: a, mocks: {sqlite: {setup: 'create tabel x'}}, expect: {output: 1}}": "setup SQL failed",
        }
        for text, msg in cases.items():
            with self.subTest(msg=msg):
                self.assert_case_fails(RESP, text, msg)


class SuiteLoadingTest(_Base):
    def make_suite(self, **attrs) -> unittest.TestSuite:
        cls = type("TestX", (OperatorTestSuite,), {"md_root": self.root, **attrs})
        return unittest.defaultTestLoader.loadTestsFromTestCase(cls)

    def run_suite(self, suite: unittest.TestSuite) -> unittest.TestResult:
        result = unittest.TestResult()
        suite.run(result)
        return result

    def test_generates_one_test_per_case(self):
        (self.root / "data").mkdir()
        (self.root / "data" / "respBuilder.yaml").write_text("name: respBuilder\nconfig: {data: 1}\n")
        (self.root / "data" / "respBuilder_input.yaml").write_text(
            "A: {desc: a, expect: {output: 1}}\nB: {desc: b, expect: {output: 2}}\n")
        suite = self.make_suite(operator="respBuilder", template="data/respBuilder.yaml")
        names = sorted(t._testMethodName for t in suite)
        self.assertEqual(names, ["test_case_A", "test_case_B", "test_register"])
        result = self.run_suite(suite)
        failed = {t._testMethodName: msg for t, msg in result.failures}
        self.assertEqual(set(failed), {"test_case_B", "test_register"})
        self.assertIn("registered as transform", failed["test_register"])  # 放错分类目录也会被发现

    def test_broken_files_become_a_failing_test(self):
        cases = [({"template": "none.yaml"}, "template not found"),
                 ({"template": "t.yaml"}, "case file not found"),
                 ({"template": "t.yaml", "operator": "expectGuard"}, "does not match declared 'expectGuard'")]
        Path(self.root / "t.yaml").write_text("name: respBuilder\nconfig: {data: 1}\n")
        for attrs, msg in cases:
            with self.subTest(msg=msg):
                result = self.run_suite(self.make_suite(**{"operator": "respBuilder", **attrs}))
                self.assertEqual(len(result.failures), 1)
                self.assertIn(msg, result.failures[0][1])

    def test_abstract_suite_generates_nothing(self):
        self.assertEqual(self.make_suite().countTestCases(), 0)


if __name__ == "__main__":
    unittest.main()
