"""配置层与编译器：目录约定、必填契约、启动期校验清单（docs/DESIGN.md §8）。"""
import os
import unittest
from unittest import mock

from lowcode.config import load_config
from lowcode.errors import ConfigError, UpstreamError

from ..support import TempConfCase, api, call

RESP = api("graph: [{name: respBuilder, config: {data: 1}}]")


class LoaderTest(TempConfCase):
    def test_file_layout_and_required_fields(self):
        # 接口必填属性缺失：validate 按字段声明顺序报第一个缺失字段
        with self.assertRaises(ConfigError) as cm:
            load_config(self.conf({"g_a_a.yaml": "graph: [{name: respBuilder, config: {data: 1}}]"}))
        self.assertIn("name: missing required field", str(cm.exception))
        with self.assertRaises(ConfigError) as cm:
            load_config(self.conf({"g_a_a.yaml": api(graph="")}))  # 只有元字段，没有 graph
        self.assertIn("graph: missing required field", str(cm.exception))

        # 文件名即路由：{模块}_{分组}_{接口}.yaml；_ / . 开头的文件忽略
        s = load_config(self.conf({"g_a_a.yaml": api("graph: [{name: respBuilder, config: {data: 1}}]",
                                                   name="我的接口", method="post", path="/g/a/a/x", desc="接口说明"),
                                   "_draft.yaml": "bad: [", "_skip_bad.yaml": "bad: [",
                                   ".hidden_bad.yaml": "bad: ["}))
        self.assertEqual([g.key for g in s.groups], ["g_a"])
        g = s.groups[0]
        self.assertEqual((g.module, g.group, g.name, g.prefix), ("g", "a", "a", "/g/a"))
        a = g.apis[0]
        self.assertEqual((a.name, a.method, a.path, a.desc), ("我的接口", "POST", "/g/a/a/x", "接口说明"))
        self.assertEqual(a.slug, "a")
        self.assertIsNone(a.graph[0].id)
        self.assertIsNone(a.graph[0].depends)

    def test_group_file_and_method_case(self):
        s = load_config(self.conf({"g_a.yaml": "{name: 组, timeout: 3}",
                                   "g_a_a.yaml": api(method="post")}))
        g = s.groups[0]
        self.assertEqual((g.name, g.prefix, g.timeout, g.apis[0].method), ("组", "/g/a", 3, "POST"))

    def test_group_prefix_is_not_configurable(self):
        # 路由前缀由文件名决定，避免"文件名说 /g/a、配置说 /v1"的不一致
        with self.assertRaises(ConfigError) as cm:
            load_config(self.conf({"g_a.yaml": "prefix: /v1", "g_a_a.yaml": RESP}))
        self.assertIn("unknown field 'prefix'", str(cm.exception))

    def test_bad_file_names(self):
        # 段数不是 2/3、名称含非法字符（下划线是分隔符）都在启动期报错
        cases = {
            "gg.yaml": "file name must be",
            "g_a_a_b.yaml": "with 4 segments",
            "g-a_x_api!.yaml": "invalid api name",
            "g_a_.yaml": "invalid api name",
        }
        for i, (name, expect) in enumerate(cases.items()):
            with self.subTest(name=name), self.assertRaises(ConfigError) as cm:
                load_config(self.conf({name: RESP}))
            self.assertIn(expect, str(cm.exception))
            (self.root / name).unlink()

    def test_structural_errors(self):
        graph_only = "graph: [{name: respBuilder, config: {data: 1}}]"
        cases = {
            api("input: []\n" + graph_only): "unknown field 'input', did you mean 'inputs'?",
            api("graph:\n  - name: a\n    depend: []\n"): "did you mean 'depends'?",
            api("graph:\n  - name: a\n    config: {x: 1, x: 2}\n"): "duplicate key 'x'",
            api("graph: [\n"): "YAML parse error (line",
            api("graph: []"): "at least one node is required",
            api("graph:\n  - name: a\n    depends: [{}]\n"): "depends[0]",
            # outputs 条目：name / type / desc 必填
            api(graph_only, outputs="[{name: a, type: int}]"): "outputs[0].desc: missing required field",
        }
        for text, expect in cases.items():
            with self.subTest(expect=expect), self.assertRaises(ConfigError) as cm:
                load_config(self.conf({"g_a_a.yaml": text}))
            self.assertIn(expect, str(cm.exception))
            (self.root / "g_a_a.yaml").unlink()

    def test_errors_collected_across_files(self):
        with self.assertRaises(ConfigError) as cm:
            load_config(self.conf({"g_a_a.yaml": "x: 1", "g_a_b.yaml": "y: 1",
                                   "h_b_c.yaml": api(path="/h/b/c")}))
        self.assertEqual(len(cm.exception.errors), 2)

    def test_env_expansion(self):
        server = "server:\n  port: ${LC_PORT}\n  host: ${LC_HOST:-0.0.0.0}\n"
        with mock.patch.dict(os.environ, {"LC_PORT": "9001"}):
            s = load_config(self.conf({"g_a_a.yaml": RESP}, server=server))
        self.assertEqual((s.port, s.host), (9001, "0.0.0.0"))
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(ConfigError) as cm:
            load_config(self.root)
        self.assertIn("environment variable LC_PORT is not set", str(cm.exception))

    def test_missing_server_or_apis(self):
        with self.assertRaises(ConfigError):
            load_config(self.root)  # 没有 server.yaml
        with self.assertRaises(ConfigError) as cm:
            load_config(self.conf({}))
        self.assertIn("no apis found", str(cm.exception))


class BuilderTest(TempConfCase):
    def build_error(self, api_text: str, server: str = None, extra=None) -> str:
        files = {"g_a_a.yaml": api_text, **(extra or {})}
        with self.assertRaises(ConfigError) as cm:
            self.runtime(files, **({"server": server} if server else {}))
        return str(cm.exception)

    def test_url_rule_and_path_params(self):
        server = "server: {prefix: /api/}\ndataSources: [{name: main, type: sqlite, config: {path: ./t.db}}]\n"
        rt = self.runtime({"g_a_b.yaml": api("graph: [{name: respBuilder, config: {data: 1}}]",
                                            path="/g/a/b/u/{uid}")}, server)
        p = rt.plans[0]
        # 前缀 /api + 文件名三段 g/a/b + path 追加段 /u/{uid}
        self.assertEqual((p.url, p.rule), ("/api/g/a/b/u/{uid}", "/api/g/a/b/u/<uid>"))
        self.assertEqual([(d.name, d.required) for d in p.inputs.defs], [("uid", True)])

    def test_default_ids_depends_and_timeout(self):
        api_text = api("""
        graph:
          - {name: sleep, config: {seconds: 0}}
          - {id: b, name: sleep, config: {seconds: 0}}
          - {name: respBuilder, config: {data: "{{ sleep }}"}}
        """, timeout=1.5)
        p = self.runtime({"g_a_a.yaml": api_text}).plans[0]
        self.assertEqual(p.levels, [["sleep"], ["b"], ["respBuilder"]])
        self.assertEqual((p.result, p.timeout), ("respBuilder", 1.5))

    def test_timeout_inheritance(self):
        rt = self.runtime({"g_a.yaml": "timeout: 3", "g_a_a.yaml": RESP,
                           "h_b_b.yaml": api(path="/h/b/b")})
        self.assertEqual({p.group.key: p.timeout for p in rt.plans}, {"g_a": 3, "h_b": 2})

    def test_graph_errors(self):
        cases = [
            ("graph: [{name: sqlQeury}]", "unknown operator 'sqlQeury', did you mean 'sqlQuery'?"),
            ("graph: [{name: respBuilder, config: {data: 1}}, {name: respBuilder, config: {data: 1}}]",
             "give each node an explicit id"),
            ("graph: [{id: inputs, name: respBuilder, config: {data: 1}}]", "is reserved"),
            ("graph: [{id: a-b, name: respBuilder, config: {data: 1}}]", "invalid node id"),
            ("graph: [{id: a, name: sleep}, {id: b, name: sleep, depends: [aa]}]", "unknown dependency 'aa', did you mean 'a'?"),
            ("graph: [{id: a, name: sleep, depends: [a]}]", "cannot depend on itself"),
            ("graph: [{id: a, name: sleep, depends: [b]}, {id: b, name: sleep, depends: [a]}]", "circular dependency"),
            ("graph: [{id: a, name: sleep}, {id: b, name: sleep, depends: []}]", "never reaches the result node 'b'"),
            ("graph: [{name: respBuilder, config: {dat: 1}}]", "did you mean 'data'?"),
            ("graph: [{name: expectGuard, config: {expect: 1, code: 0}}]", "code must not be 0"),
        ]
        for graph, expect in cases:
            with self.subTest(expect=expect):
                self.assertIn(expect, self.build_error(api(graph)))

    def test_template_reference_errors(self):
        cases = [
            ("graph: [{id: a, name: sleep}, {id: b, name: sleep, depends: [], config: {value: '{{ a }}'}},"
             " {name: respBuilder, depends: [a, b], config: {data: 1}}]",
             "referenced node 'a' is not an upstream of this node"),
            ("graph: [{name: respBuilder, config: {data: '{{ nope }}'}}]", "unknown variable 'nope'"),
            ("graph: [{name: respBuilder, config: {data: '{{ inputs.pag }}'}}]",
             "reference to undeclared input inputs.pag, did you mean 'page'?"),
            ("graph: [{name: respBuilder, config: {data: '{{ x + }}'}}]", "template syntax error"),
            ("graph: [{name: sleep, config: {seconds: '{{ 1 }}'}}]", "field seconds does not support {{ }} templates"),
        ]
        for graph, expect in cases:
            with self.subTest(expect=expect):
                inputs = "[{name: page, type: int, desc: 页码}]" if "inputs.pag" in graph else "[]"
                self.assertIn(expect, self.build_error(api(graph, inputs=inputs)))

    def test_sql_errors(self):
        q = "graph: [{name: %s, config: {sql: \"%s\", params: %s}}]"
        cases = [
            (q % ("sqlQuery", "select * from users where id = {{ x }}", "{}"), "field sql does not support {{ }} templates"),
            (q % ("sqlQuery", "select * from users where id = :id", "{}"), "bind :id in SQL is not provided in params"),
            (q % ("sqlQuery", "select * from users", "{x: 1}"), "params.x is not used in the SQL"),
            (q % ("sqlQuery", "delete from users", "{}"), "use sqlExec"),
            (q % ("sqlExec", "select 1", "{}"), "use sqlQuery"),
            (q % ("sqlQuery", "select 1", "abc"), "params must be an object"),
        ]
        for graph, expect in cases:
            with self.subTest(expect=expect):
                self.assertIn(expect, self.build_error(api(graph)))

    def test_sql_bind_names_skip_literals(self):
        api_text = api("""
        graph:
          - name: sqlQuery
            config:
              sql: "select ':x' as a, '10:30' as t -- :y\\n from users where id = :id"
              params: {id: 1}
              single: true
        """)
        self.runtime({"g_a_a.yaml": api_text})  # 引号 / 注释里的 :x、:y 不算绑定参数

    def test_outputs_contract(self):
        # 结果节点是 respBuilder 且模板为对象：模板键必须覆盖 outputs 声明
        err = self.build_error(api("graph: [{name: respBuilder, config: {data: {a: 1}}}]",
                                   outputs="[{name: b, type: int, desc: b 字段}]"))
        self.assertIn("output 'b' is missing from the response data", err)
        # 覆盖完整时通过
        self.runtime({"g_a_a.yaml": api("graph: [{name: respBuilder, config: {data: {a: 1}}}]",
                                      outputs="[{name: a, type: int, desc: a 字段}]")})
        # 整串动态 / 非 respBuilder：响应形态运行期才确定，outputs 仅作文档，不对账
        self.runtime({"g_a_a.yaml": api('graph: [{name: respBuilder, config: {data: "{{ inputs.page }}"}}]',
                                      inputs="[{name: page, type: int, desc: 页码}]",
                                      outputs="[{name: b, type: int, desc: b 字段}]")})
        self.runtime({"g_a_a.yaml": api("graph: [{name: sleep, config: {seconds: 0}}, "
                                      "{name: respBuilder, depends: [sleep], config: {data: 1}}]",
                                      outputs="[{name: b, type: int, desc: b 字段}]")})
        # 输出字段名重复（配置层）
        err = self.build_error(api("graph: [{name: respBuilder, config: {data: {a: 1}}}]",
                                   outputs="[{name: a, type: int, desc: x}, {name: a, type: int, desc: y}]"))
        self.assertIn("duplicate output field 'a'", err)

    def test_datasource_errors(self):
        sql = "graph: [{name: sqlQuery, config: {dataSource: %s, sql: select 1}}]"
        self.assertIn("datasource 'mian' not found, did you mean 'main'?", self.build_error(api(sql % "mian")))
        http = "graph: [{name: httpRequest, config: {dataSource: main, url: /x}}]"
        self.assertIn("but http is required", self.build_error(api(http)))
        self.assertIn("cannot auto-select a http datasource",
                      self.build_error(api("graph: [{name: httpRequest, config: {url: /x}}]")))
        self.assertIn("datasource 'nope' not found", self.build_error(RESP, extra={"g_a.yaml": "dataSource: nope"}))

        bad_type = "dataSources: [{name: main, type: sqlit, config: {path: ./t.db}}]"
        self.assertIn("did you mean 'sqlite'?", self.build_error(RESP, server=bad_type))
        missing = "dataSources: [{name: main, type: sqlite, config: {path: ./no.db}}]"
        self.assertIn("database file not found", self.build_error(RESP, server=missing))

    def test_datasource_entry_format(self):
        server = """dataSources:
  - {name: main, type: sqlite, paht: ./t.db}
"""
        with self.assertRaises(ConfigError) as cm:
            self.runtime({"g_a_a.yaml": RESP}, server=server)
        self.assertIn("unknown field 'paht'", str(cm.exception))

        server = """dataSources:
  - {name: main, type: sqlite, config: {path: ./t.db}}
  - {name: main, type: sqlite, config: {path: ./t.db}}
"""
        with self.assertRaises(ConfigError) as cm:
            self.runtime({"g_a_a.yaml": RESP}, server=server)
        self.assertIn("duplicate datasource 'main' (sqlite)", str(cm.exception))

    def test_same_name_across_kinds(self):
        """同名数据源可跨类别（对应 datamore_lite 同名 redis 与 mysql），按 kind 定位。"""
        server = """dataSources:
  - {name: main, type: sqlite, config: {path: ./t.db}}
  - {name: main, type: http, config: {baseUrl: 'http://127.0.0.1:1'}}
"""
        api_text = api("""
        graph:
          - id: users
            name: sqlQuery
            config: {dataSource: main, sql: 'select count(*) as n from users', params: {}, single: true}
          - name: respBuilder
            depends: [users]
            config: {data: "{{ users }}"}
        """)
        rt = self.runtime({"g_a_a.yaml": api_text}, server=server)
        self.assertEqual(len(rt.datasources.items()), 2)
        self.assertEqual(call(rt, "GET /g/a/a")[0], {"n": 5})

        # 同名的 http 数据源被 httpRequest 正确选中（不可达地址 → 502，证明走的是 http 类）
        rt2 = self.runtime({"h_b_c.yaml": api("graph: [{name: httpRequest, config: {dataSource: main, url: /x}}]",
                                              path="/h/b/c")},
                           server=server)
        with self.assertRaises(UpstreamError):
            call(rt2, "GET /h/b/c")

    def test_route_and_path_errors(self):
        graph = "graph: [{name: respBuilder, config: {data: 1}}]"
        # path 必填：完整路径，不写就报缺字段
        missing = "name: x\nmethod: GET\ndesc: d\ninputs: []\noutputs: []\n" + graph
        self.assertIn("path: missing required field", self.build_error(missing))
        # path 前三段必须与文件名一致（不允许文件名与路由各说一套）
        self.assertIn("does not match the file name", self.build_error(api(graph, path="/g/a/b")))
        self.assertIn("must start with /", self.build_error(api(graph, path="g/a/a")))
        # 追加段里：路径参数必须写成 {name}，且不能重复
        self.assertIn("path parameters must be written as",
                      self.build_error(api(graph, path="/g/a/a/<id>")))
        self.assertIn("duplicate path parameter",
                      self.build_error(api(graph, path="/g/a/a/{a}/{a}")))

    def test_errors_collected_across_apis(self):
        bad = api("graph: [{name: nope}]")
        with self.assertRaises(ConfigError) as cm:
            self.runtime({"g_a_a.yaml": bad,
                          "g_a_b.yaml": api("graph: [{name: nope}]", path="/g/a/b"),
                          "g_a_c.yaml": api(path="/g/a/c")})
        self.assertEqual(len(cm.exception.errors), 2)

    def test_structural_and_semantic_errors_reported_together(self):
        graph_only = "graph: [{name: respBuilder, config: {data: 1}}]"
        with self.assertRaises(ConfigError) as cm:
            self.runtime({"g_a_a.yaml": api("input: []\n" + graph_only),   # 结构错误（配置层）
                          "g_a_b.yaml": api("graph: [{name: nope}]", path="/g/a/b"),  # 语义错误（编译器）
                          "g_a_c.yaml": api(path="/g/a/c")})
        errors = cm.exception.errors
        self.assertEqual(len(errors), 2)
        self.assertIn("unknown field 'input'", errors[0])
        self.assertIn("unknown operator 'nope'", errors[1])


if __name__ == "__main__":
    unittest.main()
