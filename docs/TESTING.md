# 测试指南

算子测试的写法与运行方式。设计背景见 [DESIGN.md](DESIGN.md)，代码结构见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 1. 运行

```bash
# 全部
python3 -m unittest discover -s tests -t .

# 单个算子（按分类路径）
python3 -m unittest tests.operators.transformer.test_numberCast -v

# 单个用例
python3 -m unittest tests.operators.transformer.test_numberCast.TestNumberCast.test_case_Single_Object -v

# 只看目录完整性（四件套 / 参数表 / 导航登记）
python3 -m unittest tests.operators.test_catalog -v
```

当前基线：248 项通过，其中 160 个算子用例、15 个注册检查、catalog 与框架单测。

## 2. 测试目录

```
tests/
├── operators/                算子用例，目录与算子分类一一对应
│   ├── aggregate/{test_groupBy,test_listAgg}.py
│   ├── external/uhttp/test_httpRequest.py
│   ├── external/uredis/{test_redisGet,test_redisMGet}.py
│   ├── external/usql/{test_sqlExec,test_sqlQuery}.py
│   ├── filter/test_expectGuard.py
│   ├── selector/{test_fieldPicker,test_renameFields}.py
│   ├── transformer/{test_dateRange,test_numberCast,test_respBuilder,test_rowFilter,test_templateMap}.py
│   └── test_catalog.py       四件套 / 参数表 / 导航 对账
├── unit/                     框架单测（配置、编译、执行、Web、数据源）
└── support/                  临时配置、测试专用算子、Mock 工具
```

算子测试入口与代码、手册**同层级**：`lowcode/operators/<分类>/<算子>.py` ↔ `operator_md/<分类>/<算子>.*` ↔ `tests/operators/<分类>/test_<算子>.py`。

## 3. 四件套

用例执行走 `compile_node()` + `Executor.run_node()`，与线上是同一条路径。

| 文件 | 作用 | 由谁检查 |
|---|---|---|
| `operator_md/<分类>/<算子>.yaml` | 节点模板（`name` / `desc` / `config`） | catalog |
| `operator_md/<分类>/<算子>_input.yaml` | 用例集 | catalog + 用例执行 |
| `tests/operators/<分类>/test_<算子>.py` | 测试入口 | catalog |
| `operator_md/<分类>/<算子>.md` | 手册（Config 参数表） | catalog |

测试入口只有约 10 行：

```python
from lowcode.testing import OperatorTestSuite
from tests.operators import MD_ROOT

class TestNumberCast(OperatorTestSuite):
    md_root = MD_ROOT
    operator = "numberCast"
    template = "transformer/numberCast.yaml"
```

## 4. 用例字段

文件是「用例名 → 用例」的映射，用例名只能含字母 / 数字 / 下划线，会成为测试方法名 `test_case_<用例名>`。

| 字段 | 必需 | 说明 |
|---|---|---|
| `desc` | 是 | 用例说明，`-v` 时显示 |
| `config` | 否 | 覆盖节点模板的 `config`：同名替换、新键追加、写 `null` 删除 |
| `inputs` | 否 | 已校验的入参（模板里的 `{{ inputs.x }}`） |
| `request` | 否 | 请求信息（模板里的 `{{ request.x }}`） |
| `upstream` | 否 | 上游节点输出：`节点id → 值`（模板里的 `{{ 节点id }}`） |
| `mocks` | 否 | 数据源 Mock（见第 6 节） |
| `timeout` | 否 | 接口剩余时间（秒），默认 5 |
| `expect` | 是 | 期望结果，三选一 |

以 `_` 开头的顶层键是 YAML 锚点，不是用例（可用于共享 Mock 数据）。

## 5. `expect` 三选一

```yaml
# 1) 正常输出（严格比较）
expect: {output: [{date: "2026-11-04", sum: 10}]}

# 2) 运行期错误
expect:
  error:
    type: ExecError          # 异常类名
    code: 500                # 响应体业务码
    status: 500              # HTTP 状态码
    msg: "cannot compare"    # msg 应包含的片段

# 3) 构建期错误（build() 或配置校验）
expect: {buildError: "fields must be"}
```

输出比较是严格的：键顺序无关，但类型、数值、`null` 必须一致；缺少字段与 `null` 不等价。

## 6. Mock

`mocks` 为每个用例构造独立数据源，用完即释放：

```yaml
# SQLite：真实临时库，覆盖「算子 + 数据源」完整路径
mocks:
  sqlite: {name: main, setup: "create table t(id int); insert into t values (1),(2);"}
  expect: {output: [{id: 1}, {id: 2}]}

# HTTP：本地起服务，按 METHOD /path 返回
mocks:
  http:
    name: up
    routes:
      GET /ok: {json: {a: 1}}
      POST /echo: {echo: true}
      GET /slow: {delay: 3}          # 用来测超时

# Redis：内存 KV，不依赖 redis-py
mocks:
  redis:
    store:
      "counter|a": "2026-11-04|10"
      "hash": {f1: "v1"}             # 对象表示 hgetall
```

多个用例共享一份 Mock 时用 YAML 锚点：

```yaml
_db: &db {sqlite: {name: main, setup: "..."}}
Case_A: {desc: "...", mocks: *db, expect: {output: ...}}
Case_B: {desc: "...", mocks: *db, expect: {output: ...}}
```

## 7. 框架单测

`tests/unit/` 覆盖不依赖具体算子的行为：

| 文件 | 覆盖 |
|---|---|
| `test_config_builder.py` | 配置加载、命名、模板引用、outputs 对账、数据源解析 |
| `test_core.py` | 模板引擎、DAG 分层、并行、超时、错误包装 |
| `test_registry_executor.py` | 算子注册、构建期拒绝非法模板、执行顺序 |
| `test_datasources.py` | 数据源依赖探测（缺包在编译期报错） |
| `test_web.py` | 响应信封、debug、日志格式、元信息开关 |
| `test_testing.py` | 测试引擎自身（能抓住错误，而不是只会亮绿灯） |

## 8. 常见问题

| 现象 | 原因 |
|---|---|
| `unknown field 'xxx' (available: ...)` | 用例 `config` 写了算子 `spec` 没有的键 |
| `template lives in <目录>/ but operator ... is registered as ...` | 测试入口的 `template` 路径与算子分类不一致 |
| `invalid case name` | 用例名含 `-`、空格或中文 |
| `mocks` 里数据源名与节点不匹配 | Mock 的 `name` 要与节点 `dataSource` 一致，或省略走默认 |
| 期望 `null` 但实际字段缺失 | 输出比较区分「字段缺失」与「值为 null」 |
| 运行期报 `'xxx' is undefined` | 模板引用了没有声明的 `inputs.xxx` 或非上游节点 |
