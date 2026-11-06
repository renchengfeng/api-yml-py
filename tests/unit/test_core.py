"""基础层：Field 声明 / validate 校验 / 模板 / 入参 / DAG。"""
import unittest

from lowcode.config.models import InputDef
from lowcode.core.graph import Graph
from lowcode.core.inputs import InputSchema
from lowcode.core.template import compile_template
from lowcode.datasources.sqltext import bind_names, leading_keyword, to_pyformat
from lowcode.errors import ConfigError, ExecError, ParamError
from lowcode.spec import Field, child, validate

SPEC = {
    "name": Field(str, required=True),
    "size": Field(int, default=10),
    "tags": Field(list, default=[]),
    "mode": Field(str, default="a", choices=("a", "b")),
    "tpl": Field(int, dynamic=True),
}


class SpecTest(unittest.TestCase):
    def test_defaults_are_copied(self):
        a = validate({"name": "x"}, SPEC, "f")
        self.assertEqual(a["size"], 10)
        a["tags"].append(1)
        self.assertEqual(validate({"name": "x"}, SPEC, "f")["tags"], [])

    def test_unknown_field_suggests(self):
        with self.assertRaises(ConfigError) as cm:
            validate({"name": "x", "sise": 1}, SPEC, "f")
        self.assertIn("did you mean 'size'", str(cm.exception))

    def test_required_type_choices(self):
        cases = [({}, "missing required field"), ({"name": 1}, "expected string, got int: 1"),
                 ({"name": "x", "size": True}, "expected int, got bool: True"),  # bool 不能当 int
                 ({"name": "x", "mode": "c"}, "invalid value 'c'"), ("abc", "expected a mapping, got string")]
        for data, msg in cases:
            with self.subTest(data=data), self.assertRaises(ConfigError) as cm:
                validate(data, SPEC, "f")
            self.assertIn(msg, str(cm.exception))

    def test_dynamic_template_skips_type_check(self):
        self.assertEqual(validate({"name": "x", "tpl": "{{ a }}"}, SPEC, "f")["tpl"], "{{ a }}")
        with self.assertRaises(ConfigError):
            validate({"name": "x", "tpl": "abc"}, SPEC, "f")

    def test_child_path(self):
        p = child(child(child("a.yaml", "graph"), 0), "config")
        self.assertEqual(p, "a.yaml › graph[0].config")


def render(value, **scope):
    return compile_template(value, "t").render(scope)


class TemplateTest(unittest.TestCase):
    def test_whole_expression_keeps_native_type(self):
        self.assertEqual(render("{{ x }}", x=5), 5)
        self.assertEqual(render(" {{ x }} ", x=[1, 2]), [1, 2])
        self.assertEqual(render("{{ (p - 1) * s }}", p=3, s=10), 20)

    def test_mixed_text_renders_string(self):
        self.assertEqual(render("p={{ x }}", x=5), "p=5")
        self.assertEqual(render("{{ a }}-{{ b }}", a=1, b=2), "1-2")

    def test_nested_and_static(self):
        self.assertEqual(render({"a": "{{ x }}", "b": ["{{ y }}", 1]}, x=1, y="z"), {"a": 1, "b": ["z", 1]})
        self.assertTrue(compile_template({"a": 1, "b": "s"}, "t").is_static)
        self.assertFalse(compile_template({"a": "{{ x }}"}, "t").is_static)

    def test_mapping_key_wins_over_method(self):
        self.assertEqual(render("{{ row.items }}", row={"items": 3}), 3)
        self.assertEqual(render("{{ row.get('k', 0) }}", row={}), 0)
        self.assertEqual(render("{{ rows.0.name }}", rows=[{"name": "a"}]), "a")

    def test_missing_value_raises_unless_default(self):
        for src in ("{{ x.nope }}", "v={{ x.nope }}"):
            with self.subTest(src=src), self.assertRaises(ExecError):
                render(src, x={})
        self.assertEqual(render("{{ x.nope | default(7) }}", x={}), 7)

    def test_sandbox_blocks_dunder(self):
        with self.assertRaises(ExecError):
            render("{{ x.__class__.__mro__ }}", x=1)

    def test_syntax_error_is_config_error(self):
        with self.assertRaises(ConfigError):
            compile_template("{{ x + }}", "t")

    def test_refs(self):
        t = compile_template({"a": "{{ inputs.page + rows | length }}", "b": "{{ inputs['size'] }}"}, "t")
        self.assertEqual(t.names, {"inputs", "rows"})
        self.assertEqual(t.inputs, {"page", "size"})


def schema(*defs):
    return InputSchema([InputDef(**d) for d in defs], "t")


class InputsTest(unittest.TestCase):
    def test_coerce_and_default(self):
        s = schema({"name": "page", "type": "int", "default": 1}, {"name": "q"},
                   {"name": "on", "type": "bool"}, {"name": "ids", "type": "list"},
                   {"name": "f", "type": "float"}, {"name": "o", "type": "object"})
        out = s.parse({"page": "3", "on": "true", "ids": "1, 2,", "f": 2, "o": '{"a": 1}', "x": 1})
        self.assertEqual(out, {"page": 3, "q": None, "on": True, "ids": ["1", "2"], "f": 2.0, "o": {"a": 1}})
        self.assertEqual(s.parse({"page": ""})["page"], 1)  # 空串视为未传

    def test_constraints_and_aggregated_errors(self):
        s = schema({"name": "uid", "type": "int", "required": True},
                   {"name": "phone", "regex": r"^1\d{10}$"},
                   {"name": "level", "type": "int", "enum": [1, 2]},
                   {"name": "name", "min": 2, "max": 3},
                   {"name": "size", "type": "int", "max": 100})
        with self.assertRaises(ParamError) as cm:
            s.parse({"phone": "123", "level": "9", "name": "a", "size": 101})
        msg = cm.exception.msg
        for part in ("uid 必填", "phone 格式不正确", "level 取值应为", "name 长度不能小于 2", "size 不能大于 100"):
            self.assertIn(part, msg)
        with self.assertRaises(ParamError):
            schema({"name": "n", "type": "int"}).parse({"n": True})

    def test_declaration_errors(self):
        bad = [{"name": "a", "type": "int", "default": "x"}, {"name": "a", "required": True, "default": "x"},
               {"name": "a", "type": "int", "regex": "x"}, {"name": "a", "regex": "("},
               {"name": "1a"}, {"name": "a", "type": "bool", "max": 1}]
        for d in bad:
            with self.subTest(d=d), self.assertRaises(ConfigError):
                schema(d)
        with self.assertRaises(ConfigError):
            schema({"name": "a"}, {"name": "a"})


class GraphTest(unittest.TestCase):
    def test_levels_and_ancestors(self):
        g = Graph({"a": [], "b": [], "c": ["a", "b"], "d": ["c"]})
        self.assertEqual(g.levels(), [["a", "b"], ["c"], ["d"]])
        self.assertEqual(g.ancestors("d"), {"a", "b", "c"})

    def test_cycle(self):
        with self.assertRaises(ConfigError) as cm:
            Graph({"a": [], "b": ["c"], "c": ["b"]}).levels()
        self.assertIn("circular dependency: b, c", str(cm.exception))


class SqlTextTest(unittest.TestCase):
    SQL = "select ':x', '10:30', a::int /* :c */ from t -- :d\nwhere id = :id and n like '50%' and k = :k or id = :id"

    def test_bind_names_skip_literals_comments_and_casts(self):
        self.assertEqual(bind_names(self.SQL), ["id", "k"])
        self.assertEqual(leading_keyword("  -- note\n/* x */ SELECT 1"), "select")

    def test_to_pyformat_for_mysql(self):
        self.assertEqual(to_pyformat("select * from t where a = :a and b like '%x' and c % 2 = :c"),
                         "select * from t where a = %(a)s and b like '%%x' and c %% 2 = %(c)s")
        self.assertIn("':x'", to_pyformat(self.SQL))  # 引号内保持原样


if __name__ == "__main__":
    unittest.main()
