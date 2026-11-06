# 架构说明

本文回答「代码是怎么组织的、一次请求经过哪些函数」。设计取舍与配置规范见 [DESIGN.md](DESIGN.md)。

## 1. 定位

api-yml-py 是一个**配置编译型**框架，不是解释执行型：

- 启动时把 YAML 编译成 `ApiPlan`（节点、依赖、静态参数、已编译模板）；
- 请求时只做「入参校验 → 模板渲染 → 调算子 → 写黑板 → 组响应」，不再解析 YAML。

因此配置错误、模板引用错误、缺依赖都在**启动期**暴露，而不是等第一个请求。

## 2. 分层与依赖方向

```
        web / __main__          入口：HTTP 与 CLI
              │
        runtime.build_runtime   唯一装配点
        ┌─────┼─────────┬──────────────┐
     config  core      operators    datasources
        └─────┴─────────┴──────────────┘
                  │
             spec / errors          基础契约
```

| 层 | 职责 | 依赖 |
|---|---|---|
| `spec` / `errors` | 字段声明与校验、错误类型 | 无 |
| `config` | YAML → `ServerDef / GroupDef / ApiDef / NodeDef` | spec / errors |
| `operators` | 算子契约与内置算子 | spec / errors / datasources（外部算子） |
| `core` | 编译（builder/template/graph）与执行（executor/context） | config / operators |
| `datasources` | sqlite / mysql / redis / http | errors |
| `web` / `runtime` | 装配、路由、响应、日志 | 以上全部 |

`web` 与 `__main__` 只依赖 `runtime.build_runtime()`，彼此互不知道。

## 3. 目录与职责

| 路径 | 职责 | 关键入口 |
|---|---|---|
| `lowcode/spec.py` | `Field` 声明、`validate()`、`is_template()`、报错定位 | `validate(config, spec, where)` |
| `lowcode/errors.py` | 错误分层与汇总 | `ConfigError` / `ParamError` / `BizError` / `UpstreamError` / `DeadlineError` / `ExecError`、`ErrorCollector` |
| `lowcode/config/loader.py` | 扫描目录、解析 YAML、结构校验 | `load_config()` / `load_node()` / `read_yaml()` |
| `lowcode/config/models.py` | 配置模型与 `*_SPEC`（含 `logFile` / `logBackup`） | `ServerDef` / `GroupDef` / `ApiDef` / `NodeDef` / `InputDef` / `OutputDef` |
| `lowcode/runtime.py` | 装配根 | `build_runtime()` → `Runtime` |
| `lowcode/core/builder.py` | 把 `ApiDef` 编成 `ApiPlan` | `Builder.build()` / `build_api()` / `compile_node()` / `_compile_config()` |
| `lowcode/core/template.py` | `{{ }}` 编译与渲染 | `compile_template()` / `Template.render()` |
| `lowcode/core/graph.py` | DAG 分层、环检测、可达性 | `Graph.levels()` / `ancestors()` |
| `lowcode/core/inputs.py` | 入参校验器 | `InputSchema.parse()` |
| `lowcode/core/executor.py` | 按层执行 | `Executor.run()` / `run_node()` |
| `lowcode/core/context.py` | 请求级黑板 | `scope()` / `set_output()` / `record()` |
| `lowcode/operators/base.py` | 算子契约 | `Operator.build()` / `execute()` |
| `lowcode/operators/registry.py` | 注册表与编译期工厂 | `register()` / `get_operator()` / `create_operator()` |
| `lowcode/operators/<分类>/` | 15 个内置算子 | 见 [算子导航](../operator_md/算子导航.md) |
| `lowcode/datasources/` | 数据源实现 | `DataSource` / `DataSourceManager.resolve()` |
| `lowcode/server.py` | 库式入口：app + runtime + 生命周期 | `Lowcode(conf).run()` / `close()` / `__call__`（WSGI） |
| `lowcode/web/app.py` | Flask 应用工厂、路由、钩子 | `create_app()` / `view()` |
| `lowcode/web/response.py` | 统一响应信封 | `envelope()` |
| `lowcode/testing/` | 算子测试引擎 | `OperatorTestSuite` / `load_cases()` / `run_case()` |

## 4. 三条链路

### 4.1 启动装配

```
build_runtime(conf_dir)
  ├─ load_config()                     YAML → ServerDef（含 groups → apis → nodes）
  ├─ DataSourceManager.from_config()   实例化数据源 + check()（不连网）
  ├─ Builder(server, ds).build()       逐接口编译（见 4.2）
  ├─ ErrorCollector.raise_if_any()     结构/语义错误一次性抛出
  └─ Executor(...)                     线程池
```

`server.yaml` 或数据源有误会立即中止；单个接口文件有误只跳过该文件，其余继续编译，以便一次暴露全部问题。

### 4.2 编译（`ApiDef → ApiPlan`）

```
Builder.build_api(group, api)
  ├─ InputSchema(...)                  入参校验器
  ├─ Graph({id: depends}).levels()     拓扑分层（同层可并行）
  ├─ compile_node(node, env, ...)      每个节点
  │    ├─ create_operator()            查表 → 防注入 → validate() → 实例化 → build()
  │    └─ _compile_config()            拆 static / dynamic / raw + compile_template() + _check_refs()
  └─ _check_outputs()                  结果节点为 respBuilder 时，模板键与 outputs 对账
```

产物 `ApiPlan` 包含：`inputs`、`nodes`（每个 `PlanNode` = 算子实例 + 静态参数 + 已编译模板）、`levels`、`result`（graph 最后一个节点）、`timeout`。

### 4.3 请求（一次 HTTP 请求）

```
view()
  ├─ plan.inputs.parse()              入参校验 → inputs
  ├─ Context(inputs, request, traceId)
  ├─ executor.run(plan, ctx)          逐层
  │    └─ run_node(node, ctx)         所有节点执行的唯一入口
  │         ├─ node.resolve_args(ctx.scope())   静态原样 + dynamic 渲染
  │         ├─ node.op.execute(ctx, args)       算子干活
  │         ├─ ctx.set_output(node.id, value)   写黑板
  │         └─ ctx.record(...)                  finally 记 trace
  └─ envelope(0, "ok", data, traceId)
```

`run_node` 是所有节点执行的唯一入口；算子测试框架也走它，所以测试路径与线上一致。

## 5. 数据源解析顺序

算子通过 `env.datasource(name, kind)` 取数据源，顺序为：

1. 节点 `config.dataSource`；
2. 分组 `<module>_<group>.yaml` 的 `dataSource`（类别相符时）；
3. 该类别唯一的数据源。

解析成功后会调用 `check_dependencies()` 探测可选包，缺包在**编译该接口时**报错；连接延迟到首次使用。
各类数据源的配置字段见 [DESIGN.md · 数据源](DESIGN.md#6-数据源)。

## 6. 扩展点

| 想做什么 | 改哪里 |
|---|---|
| 新增算子 | `lowcode/operators/<分类>/` + 分类 `__init__.py` + 四件套 + 导航 |
| 新增数据源 | 实现 `DataSource` 子类 + `@register_datasource` + 在 `datasources/__init__.py` 导入 |
| 新增接口 | 在 `conf/` 加 `{module}_{group}_{api}.yaml` |
| 改响应信封 | `web/response.py::envelope()` |
| 改日志格式 | `web/app.py::_log()` |

## 7. 运行方式

| 方式 | 命令 | 入口 |
|---|---|---|
| 库入口 | `python3 main.py` / `PORT=9000 python3 main.py` | `main.py` → `Lowcode` → `create_app` → `build_runtime` |
| CLI | `python3 -m lowcode serve -c conf` | `__main__._serve` → `create_app` |
| WSGI | `gunicorn -w 4 'main:server'` | `Lowcode.__call__` → Flask app |

`Lowcode`（`lowcode/server.py`）把 app、runtime、`run()`、`close()` 与 WSGI 调用收在一个对象里；
`create_app()` 仍保留，供只需要 Flask app 的场景使用。
