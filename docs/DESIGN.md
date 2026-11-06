# 设计说明

本文回答「为什么这样设计、配置怎么写、边界在哪」。代码结构见 [ARCHITECTURE.md](ARCHITECTURE.md)，测试写法见 [TESTING.md](TESTING.md)。

## 1. 目标与取舍

| 目标 | 做法 | 代价 |
|---|---|---|
| 接口开发不写 Python | 一个接口一个 YAML，算子组合 | 复杂逻辑仍需写算子 |
| 错误尽早暴露 | 启动期编译、校验、依赖探测 | 启动稍慢，配置约束严格 |
| 数据流清晰 | 节点按 id 写黑板，下游 `{{ id }}` 读 | 依赖关系需要显式 `depends` |
| 算子可插拔 | `@register` + `spec` + 四件套 | 每个算子要有手册与用例 |
| 请求隔离 | 每次请求独立 `Context` | 不能跨请求共享可变状态 |

**不追求**：把 YAML 变成编程语言（不提供分支/循环）、通用工作流编排（只做 HTTP 接口）。

## 2. 四层模型

```
server.yaml                 ServerDef   端口 / 前缀 / 超时 / 数据源
  {module}_{group}.yaml     GroupDef    可选：分组默认数据源、超时、前缀
    {module}_{group}_{api}.yaml  ApiDef  一个文件一个接口：inputs / outputs / graph
      graph[]               NodeDef     算子节点：name / id / depends / config
```

文件名三段决定路由：`demo_counter_merge.yaml` → `/api/demo/counter/merge`（`prefix` 默认 `/api`）。
接口里的 `path` 必须与文件名一致，启动期校验；下划线是分隔符，段名不能含下划线。

## 3. 配置规范

### 3.1 文件命名

| 文件 | 作用 | 必需 |
|---|---|---|
| `server.yaml` | 服务公共配置 | 是 |
| `{module}_{group}.yaml` | 分组配置（所有字段可选） | 否 |
| `{module}_{group}_{api}.yaml` | 一个接口一个文件 | 是 |

以 `_` 或 `.` 开头的文件、非 YAML 文件会被忽略（可用来临时下线）。

### 3.2 `server.yaml`

```yaml
name: "demo"
server:
  host: 127.0.0.1
  port: ${PORT:-8080}
  prefix: /api
  timeout: 5
  debug: true            # 5xx 返回详细错误；节点耗时只进日志
dataSources:
  - {name: "main", type: sqlite, config: {path: ../data/demo.db}}
  - {name: "redis1", type: redis, config: {address: "dns://localhost:6379", password: "12345678"}}
```

- 数据源按 `{name, type, config}` 声明；同名可跨类别（按 `(name, kind)` 区分）；
- `${VAR:-默认值}` 从环境变量注入，适合放密码；
- `debug` 只影响 5xx 是否对外暴露详细错误。

### 3.3 分组文件（可选）

```yaml
name: "用户分组"
dataSource: "main"     # 该分组节点的默认数据源
timeout: 3             # 覆盖 server.timeout
prefix: /v1            # 覆盖 server.prefix
```

### 3.4 接口文件

```yaml
name: "Redis 双键按日期合并计数"
method: GET
path: "/demo/counter/merge"     # 必须与文件名一致
desc: "读取两个 key，按日期合并计数"
timeout: 5                      # 可选
inputs:
  - {name: "date", type: string, required: true, desc: "统计日期"}
  - {name: "cnt", type: int, required: true, min: 0, desc: "阈值"}
outputs: []                     # 结果节点为 respBuilder 时用于对账
graph: [ ... ]
```

### 3.5 节点 `graph[]`

| 字段 | 必需 | 说明 |
|---|---|---|
| `name` | 是 | 算子注册名 |
| `id` | 否 | 缺省等于 `name`；同一 graph 内唯一 |
| `depends` | 否 | 缺省为上一个节点；`[]` 表示根节点 |
| `desc` | 否 | 节点在做什么，进 `/_apis` 与日志 |
| `config` | 是 | 算子参数，键由算子 `spec` 决定 |

**结果节点 = graph 最后一项**，它的输出就是响应 `data`。

### 3.6 `inputs[]` / `outputs[]`

入参字段：`name`、`type`（`string / int / float / bool / list / object`）、`required`、`default`、`desc`、`regex`、`enum`、`min`、`max`。
`desc` 必填，用于 `/_apis` 与 `explain`。

`outputs[]` 是响应契约：结果节点为 `respBuilder` 且模板是对象时，模板键必须覆盖 `outputs` 声明的字段，否则启动期报错。

### 3.7 模板 `{{ }}`

可引用的命名空间：

| 来源 | 写法 | 说明 |
|---|---|---|
| 入参 | `{{ inputs.date }}` | 必须是已声明的入参 |
| 请求 | `{{ request.path }}`、`request.query` 等 | method / path / headers / query / body / remoteAddr |
| 上游节点 | `{{ a }}`、`{{ a.cnt }}`、`{{ [a, b] }}` | 必须在 `depends` 链上 |
| Jinja 全局 | `{{ range(3) }}`、`{{ rows \| length }}` | 沙箱内可用 |

规则：

- **整串单表达式保留原生类型**：`"{{ cast }}"` 得到 list；`"hello, {{ inputs.name }}"` 得到字符串；
- 字典 / 列表会递归渲染；
- 引用不存在的字段运行期报错，需要兜底写 `| default(...)`。

## 4. 算子框架

### 4.1 接口

```python
@register("numberCast", category="transformer")
class NumberCast(Operator):
    spec = {
        "data": Field(object, required=True, dynamic=True, desc="对象或对象列表"),
        "fields": Field(list, required=True, desc="要转成数值的字段"),
    }

    def build(self) -> None:        # 启动期一次：校验配置、取数据源
        ...

    def execute(self, ctx, args):   # 每请求一次：只处理数据
        ...
```

### 4.2 三类 config 字段

| 类型 | 声明 | 行为 |
|---|---|---|
| static | 默认 | 启动期固化，请求期原样使用 |
| dynamic | `dynamic=True` | 启动期编译成 `Template`，请求期用 scope 渲染 |
| raw | `raw=True` | 框架不编译不校验，算子自己渲染（如 `templateMap.template`） |

非 `dynamic` / `raw` 字段写 `{{ }}` 会在启动期直接报错（防注入）。

### 4.3 一个算子的五步

1. **注册**：`@register` 写入全局表，校验命名（camelCase）、`spec` 类型、重名；
2. **编译**：`create_operator()` 查表 → 防注入检查 → `validate()` → 实例化 → `build()`；
3. **渲染**：`PlanNode.resolve_args(scope)` 渲染 dynamic 字段；
4. **执行**：`execute(ctx, args)` 返回输出；
5. **记录**：输出写黑板，`Context.record()` 记耗时与错误。

### 4.4 分类与单一职责

框架共 6 类、52 个内置算子。每个分类用一个可判定问题定义，按顺序判断：

| 顺序 | 分类 | 判定标准（是 → 归入） | 输出 | 副作用 |
|---|---|---|---|---|
| 1 | `external` | 读写框架外部资源（DB / HTTP / Redis / 文件系统 / 压缩包落地）？ | 数据或写入结果 | 允许 I/O |
| 2 | `filter` | 条件不满足即中断请求（抛 `BizError`）？ | 透传 | 中断接口 |
| 3 | `aggregate` | 把多行归约成统计量？ | 统计量 | 无 |
| 4 | `validate` | 按规则检查并产出报告 `{valid, errors}`，不中断？ | 报告 | 无 |
| 5 | `selector` | 只从已有值中选取 / 投影 / 重命名 / 二选一？ | 原值子集 | 无 |
| 6 | `transformer` | 其余纯数据变换：输入 → 新值，无外部 I/O | 新值 | 无 |

`external` 内部按系统分 `usql / uhttp / uredis / ufs`；其余分类扁平。
原则：一个算子只做一件事；新增算子先按上表判定分类，缺能力时不给现有算子加模式开关。

两个标注：`fsTransaction` 是组合型外部写操作（多步 + 补偿），按副作用归 `external`；
`pickValue` 只是二选一取值，`branch` 已改名，避免与「不提供分支/循环」的设计决策冲突。

## 5. 执行引擎

- **分层**：`Graph.levels()` 拓扑分层，层间串行、同层可并行（`server.parallel`）；
- **黑板**：`Context._outputs` 保存节点输出，`scope()` 返回副本 + `inputs` + `request`；
- **快速失败**：同层任一节点失败立即返回，按定义顺序取第一个错误；
- **超时**：`Context.deadline` + `remaining()`，每层前检查，算子可通过 `ctx` 感知剩余时间；
- **不可变**：算子不得原地修改 `args` 或上游输出，必须返回新对象（契约测试强制）。

## 6. 数据源

| 类别 | 方法 | 实现 |
|---|---|---|
| `sql` | `query()` / `execute()` | sqlite / mysql（`sourceName` 或 host 五件套） |
| `kv` | `get()` / `hgetall()` / `mget()` | redis（`url` 或 `address` + 密码） |
| `http` | `request()` | http（`baseUrl` / 公共 headers / 超时） |

- 连接池参数（`maxOpenConn` 等）为兼容预留字段，当前每次调用新建连接。

## 7. 响应、错误与日志

响应固定：

```json
{"code": 0, "msg": "ok", "traceId": "…", "data": …}
```

算子也可返回 `lowcode.RawResponse`（payload / status / headers），Web 层直接输出原始 HTTP、绕过信封；
这是文件下载、二进制内容与自定义状态码的通用出口。

| 错误 | HTTP | 说明 |
|---|---|---|
| `ParamError` | 400 | 入参校验，错误一次列全 |
| `BizError` | code（400-599）或 200 | 业务中断，`expectGuard` 使用 |
| `UpstreamError` | 502 | 上游失败 |
| `DeadlineError` | 504 | 超时 |
| `ExecError` | 500 | 非预期异常，带 `[节点id]` |
| `ConfigError` | — | 启动期，不产生响应 |

日志一行一个字符串，`k=v` + `|`；字段顺序 `caller / time / level / logger / traceId / event / …`，`caller=文件:行号` 由日志格式提供（`stacklevel` 指向真实调用点）。
每个请求输出两行：`event=request` 汇总（`nodes` 只含节点 id 与耗时），`event=nodes` 明细（`detail=` 含算子与说明）。
响应体**永远不含 trace**，节点耗时只写服务端日志。

`server.logFile` 非空时同时写文件：相对路径以 `server.yaml` 所在目录（`conf/`）为基准，示例 `../logs/api-yml-py.log` 写到项目根 `logs/`，编码 UTF-8，
每天一个文件 `app-YYYY-MM-DD.log`（`DailyFileHandler`，跨天自动切换，保留 `logBackup` 天）。
多进程部署时切分由各进程独立触发，建议生产环境把 `logFile` 留空、交给 gunicorn / 外部 logrotate。

## 8. 启动期校验清单

- 文件名三段合法，`path` 与文件名一致；
- `server.yaml` 必需字段齐全，数据源 `type` 已注册；
- 每个节点 `name` 已注册，`config` 键与 `spec` 完全匹配（未知键报错并给建议）；
- 非 dynamic 字段没有写 `{{ }}`；
- 模板引用的节点在 `depends` 链上，`inputs.xxx` 已声明；
- 依赖缺失（redis-py / pymysql）在编译使用它的接口时报错；
- `outputs` 与 `respBuilder` 模板键对账；
- 数据源在节点 / 分组 / 唯一类别中可解析。

## 9. 关键设计决策

| 决策 | 理由 | 代价 |
|---|---|---|
| 启动期编译成 ApiPlan | 请求期零解析，错误前置 | 启动慢、配置约束严 |
| 一个接口一个文件 | 路由可预测，diff 清晰 | 接口多时文件多 |
| 节点按 id 写黑板 | 数据流显式、可并行 | 依赖需显式声明 |
| 算子单一职责 | 组合优于开关，手册/用例稳定 | 简单功能也需要新算子 |
| `spec` 三类字段 | 静态性能 + 动态灵活 + raw 逃生口 | 概念多一层 |
| 不提供分支/循环 | 避免 YAML 变编程语言 | 复杂流程需写算子 |
| 四件套强制 | 手册、用例与代码同步 | 新增算子成本高 |
| 错误分层 | 调用方只看 code/msg，开发者看日志 | 需要理解层级 |

## 10. 已知限制与扩展方向

- 不支持跨接口复用 graph 片段（只能复制或写算子）；
- 结果为最后节点，暂不支持显式 `result`；
- 无内置鉴权/限流，建议放在网关或 Flask 中间件；
- 数据源连接池未实现；
- 分布式/重试/补偿需外部系统承担。
