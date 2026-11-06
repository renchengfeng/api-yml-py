"""算子目录完整性检查：保证手册、模板、用例、测试入口与代码始终一致。

对每个内置算子检查：
  1. 四件套齐全：<分类>/<名字>.md、.yaml、_input.yaml，以及 tests/operators 中的测试套件；
  2. 模板路径与注册分类一致（external 下可再按数据源分子目录，如 external/usql/）；
  3. 手册「Config 参数」表与代码中的 spec 一致：字段名与顺序、是否必填、是否支持模板；
  4. 算子导航页已登记；
  5. 反向检查：operator_md 中没有已经不存在的算子的残留文档。
"""
import importlib
import pkgutil
import re
import unittest
from pathlib import Path
from typing import Dict, List, Type

from lowcode.operators import Operator, list_operators
from lowcode.testing import OperatorTestSuite

from tests.operators import MD_ROOT

_CELL_SPLIT = re.compile(r"(?<!\\)\|")  # 按未转义的 | 切分表格单元格
_CHECK = "✅"


def config_table(md: Path) -> List[Dict[str, str]]:
    """解析手册中「## Config 参数」一节的表格，返回每行的 {key, required, dynamic}。"""
    text = md.read_text(encoding="utf-8")
    m = re.search(r"^## Config 参数\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    rows = []
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in _CELL_SPLIT.split(line.strip())[1:-1]]
        if len(cells) >= 5 and cells[0].startswith("`"):
            rows.append({"key": cells[0].strip("`"), "required": cells[2], "dynamic": cells[4]})
    return rows


def builtin_operators() -> List[Type[Operator]]:
    """所有内置算子：模块都在 lowcode.operators 包下（导入即注册）。"""
    return [op for op in list_operators() if op.__module__.startswith("lowcode.operators.")]


def suite_operators() -> Dict[str, Type[OperatorTestSuite]]:
    """tests/operators 下所有测试套件：算子名 → 套件类。"""
    found: Dict[str, Type[OperatorTestSuite]] = {}
    package = importlib.import_module(__package__)
    for info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        module = importlib.import_module(info.name)
        for obj in vars(module).values():
            if isinstance(obj, type) and issubclass(obj, OperatorTestSuite) and obj.operator:
                found[obj.operator] = obj
    return found


class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builtins = builtin_operators()
        cls.suites = suite_operators()
        cls.nav = (MD_ROOT / "算子导航.md").read_text(encoding="utf-8")

    def assert_doc_matches_spec(self, md: Path, op: Type[Operator]) -> None:
        rows = config_table(md)
        where = md.relative_to(MD_ROOT.parent)
        self.assertEqual([r["key"] for r in rows], list(op.spec),
                         f"{where} config table does not match {op.name}.spec (fields and order)")
        for r in rows:
            f = op.spec[r["key"]]
            self.assertEqual(r["required"] == _CHECK, f.required, f"{where}: required column of {r['key']} does not match spec")
            self.assertEqual(r["dynamic"] == _CHECK, f.dynamic, f"{where}: dynamic column of {r['key']} does not match spec")

    def test_builtin_operators_are_fully_documented_and_tested(self):
        self.assertTrue(self.builtins)
        for op in self.builtins:
            with self.subTest(operator=op.name):
                suite = self.suites.get(op.name)
                self.assertIsNotNone(suite, f"missing test entry tests/operators/test_{op.name}.py")
                tpl = Path(suite.template)
                self.assertTrue(tpl.parts[0] == op.category or tpl.as_posix().startswith(op.category + "/"),
                                f"template {suite.template} does not match category {op.category} of operator {op.name}")
                base = MD_ROOT / tpl.parent / op.name  # <分类>/<算子名>.{md,yaml} 与 _input.yaml
                for suffix in (".md", ".yaml", "_input.yaml"):
                    path = Path(f"{base}{suffix}")
                    self.assertTrue(path.is_file(), f"missing {path.relative_to(MD_ROOT.parent)}")
                self.assert_doc_matches_spec(Path(f"{base}.md"), op)
                # 用 assertTrue 而不是 assertIn：后者失败时会把整页导航内容打印出来
                link = f"[{op.name}]({tpl.with_suffix('.md').as_posix()})"
                self.assertTrue(link in self.nav, f"operator navigation does not list {op.name}")

    def test_no_stale_docs(self):
        """operator_md 下（除导航页）每个 md 都必须对应一个已注册的内置算子。"""
        expected = {Path(self.suites[op.name].template).with_suffix(".md").as_posix()
                    for op in self.builtins}
        for md in MD_ROOT.rglob("*.md"):
            rel = md.relative_to(MD_ROOT).as_posix()
            if rel == "算子导航.md":
                continue
            with self.subTest(doc=rel):
                self.assertIn(rel, expected,
                              f"{rel} has no matching operator (renamed / deleted / moved?)")


class ConfigTableParserTest(unittest.TestCase):
    """解析器自身：转义的 \\| 不应被当作列分隔。"""

    def test_escaped_pipe(self):
        rows = config_table(MD_ROOT / "external" / "uredis" / "redisGet.md")
        delimiter = next(r for r in rows if r["key"] == "delimiter")
        self.assertEqual((delimiter["required"], delimiter["dynamic"]), ("", ""))


if __name__ == "__main__":
    unittest.main()
