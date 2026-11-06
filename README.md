# api-yml-py

YAML 驱动的 Flask 低代码 HTTP 框架。用 **server → group → api → 算子** 四层模型描述接口：
写配置就能得到 HTTP 接口，不需要为每个接口写 Python。

```yaml
# conf/demo_counter_merge.yaml → GET /api/demo/counter/merge
name: "Redis 双键按日期合并计数"
method: GET
path: "/demo/counter/merge"
inputs:
  - {name: "date", type: string, required: true, desc: "统计日期"}
  - {name: "cnt", type: int, required: true, min: 0, desc: "只返回加和大于该值的分组"}
graph:
  - {id: a, name: "redisGet", config: {dataSource: "redis1", key: "counter|daily|a|{{ inputs.date }}", format: csv, fields: [date, cnt]}}
  - {id: b, name: "redisGet", config: {dataSource: "redis1", key: "counter|daily|b|{{ inputs.date }}", format: csv, fields: [date, cnt]}}
  - {id: cast, name: "numberCast", depends: [a, b], config: {data: "{{ [a, b] }}", fields: [cnt]}}
  - {id: grouped, name: "groupBy", depends: [cast], config: {data: "{{ cast }}", by: date, field: cnt, ops: [sum]}}
  - {id: filtered, name: "rowFilter", depends: [grouped], config: {data: "{{ grouped }}", field: sum, op: gt, value: "{{ inputs.cnt }}"}}
  - {name: "respBuilder", depends: [filtered], config: {data: "{{ filtered }}"}}
```

## 特性

- **一个接口一个文件**：`{module}_{group}_{api}.yaml` → `/api/{module}/{group}/{api}`，文件名与 `path` 启动期强校验
- **算子即插件**：`@register("name", category=...)` + `spec` 声明 config，`build()` 启动期一次、`execute()` 每请求一次
- **启动期编译成 ApiPlan**：结构、依赖、模板引用、`outputs` 对账、数据源依赖全部前置校验，错误一次列全
- **请求期 DAG 执行**：拓扑分层、同层并行、超时控制；节点输出写入请求级黑板，下游用 `{{ 节点id }}` 取数
- **统一模板**：`{{ inputs.x }}` / `{{ request.path }}` / 上游节点 id；整串单表达式保留原生类型
- **数据源可插拔**：SQLite / MySQL / Redis / HTTP；MySQL、Redis 为可选 extras
- **可观测**：响应固定 `{code, msg, traceId, data}`；服务端一行一条 `k=v` 日志，按 `traceId` 串起一次请求
- **自带元信息**：`/_health`、`/_apis`（DAG / 节点说明 / 响应骨架）、`/_operators`、`explain` 离线解释

## 快速上手

分发名是 **`api-yml-py`**（模块名仍是 `api-yml-py`，`import lowcode` 不变）：

```bash
pip install -e .                         # 安装框架（核心依赖 Flask + PyYAML）
pip install -e ".[redis]"                # 可选：Redis / MySQL 数据源

python3 data/make_db.py                  # 生成演示库 data/demo.db
python3 -m lowcode check -c conf         # 只校验配置，打印路由表
```

### 启动服务

| 方式 | 命令 | 说明 |
|---|---|---|
| 库入口（推荐） | `python3 main.py` | 读 `conf/server.yaml`，默认 `127.0.0.1:8080` |
| 换端口启动 | `PORT=9000 python3 main.py` | `server.yaml` 中 `port: ${PORT:-8080}` |
| CLI 启动 | `python3 -m lowcode serve -c conf` | 等价启动方式 |
| 生产部署 | `gunicorn -w 4 'main:server'` | `Lowcode` 实例本身是 WSGI app |

`main.py` 只有三行有效代码：

```python
from lowcode import Lowcode

server = Lowcode("conf")     # 解析配置、编译接口；失败抛 ConfigError

if __name__ == "__main__":
    server.run()             # host / port 缺省读 server.yaml
```

端口优先级：`PORT` 环境变量 → `server.yaml` 的 `server.port`；`--port` 或 `server.run(port=...)` 可再覆盖。

两个演示接口都从 Redis 取数（`conf/server.yaml` 的 `redis1` 数据源，默认 `localhost:6379`、密码 `12345678`）：

```bash
redis-cli -a 12345678 --no-auth-warning set "counter|daily|a|20261104" "20261104|66"
redis-cli -a 12345678 --no-auth-warning set "counter|daily|b|20261104" "20261104|77"

curl 'http://127.0.0.1:8080/api/demo/counter/merge?date=20261104&cnt=10'
# {"code":0,"msg":"ok","traceId":"…","data":[{"date":"20261104","sum":143}]}

curl 'http://127.0.0.1:8080/api/demo/counter/range?sday=20261103&eday=20261104&cnt=10'

curl 'http://127.0.0.1:8080/_apis'       # 所有接口：分层、节点说明、响应结构
curl 'http://127.0.0.1:8080/_operators'  # 所有算子及 config 字段
python3 -m lowcode explain -c conf       # 离线看每个接口的节点与响应结构
```

## 配置长什么样

```
conf/
├── server.yaml                 # 第一层 server：端口 / 前缀 / 超时 / 数据源
├── demo_counter_merge.yaml     # 第三层 api：{模块}_{分组}_{接口}.yaml
└── demo_counter_range.yaml     #   模块 demo / 分组 counter / 接口 range
```

第二层 group 配置 `{模块}_{分组}.yaml` 可选（可设默认数据源、超时、前缀），示例里没有，所以节点直接写 `dataSource`。

文件名三段决定路由，接口里的 `path` 必须显式写出并与之一致；下划线是分隔符，接口名不能含下划线。
需要路径参数时把追加段写进 `path`，如 `path: "/user/profile/detail/{uid}"`。

## 日志

默认输出到控制台；配置 `logFile` 后同时写入文件，**每天一个文件、文件名带日期**（保留 `logBackup` 天）：

```yaml
server:
  logLevel: INFO
  logFile: "../logs/api-yml-py.log"  # 相对 server.yaml 所在目录（conf/），此处写到项目根 logs/；留空 = 只输出控制台
  logBackup: 7                  # 切分后保留天数
```

每个请求输出两行（`traceId` 相同，可按 `traceId` 关联）：

- `event=request`：`method / path / status / ms / nodes`，`nodes` 只列「节点ID + 耗时」；
- `event=nodes`：`detail=` 列「节点ID(算子) 耗时 说明」，便于定位每个节点做了什么。

格式固定为 `caller=文件:行号|time=…|level=…|logger=lowcode|traceId=…|event=…|…`，`caller` 是日志打印位置（默认格式下由 handler 补充）；
实际文件名形如 `../logs/api-yml-py-2026-11-06.log`（即项目根的 `logs/`）；跨天自动切换到新文件，早于保留天数的旧文件会被删除。

> 多进程部署（`gunicorn -w 4`）时各进程会独立触发切分，建议 `logFile` 留空，交给 gunicorn 的
> `--access-logfile/--error-logfile` 或外部 logrotate 统一收集。

## 算子

内置 52 个算子，按职责分六类：`external`（外部资源 I/O）、`filter`（断言中断）、`aggregate`、
`validate`（校验报告）、`selector`（字段选取）、`transformer`（纯数据变换）。

完整列表、参数、选型与「新增算子」步骤见 **[operator_md/算子导航.md](operator_md/算子导航.md)**；
运行时可用 `/_operators` 或 `api-yml-py operators` 查看。

## 目录

```
lowcode/        框架实现
  config/       YAML → ServerDef / GroupDef / ApiDef / NodeDef
  core/         编译（builder/template/graph/inputs）与执行（executor/context）
  operators/    算子：aggregate / external / filter / selector / transformer
  datasources/  sqlite / mysql / redis / http
  web/          Flask 装配与统一响应
  testing/      算子测试引擎（随包分发）
conf/           示例配置（两个 Redis 计数接口）
operator_md/    算子手册：<分类>/<算子>.md / .yaml / _input.yaml
tests/          operators/（按分类的算子用例）+ unit/（框架单测）+ support/
data/           SQLite 演示库与建库脚本
docs/           架构、设计、测试文档与图示
```

## 文档

- [架构说明](docs/ARCHITECTURE.md) — 分层、目录职责、启动/编译/请求链
- [设计说明](docs/DESIGN.md) — 四层模型、配置规范、算子框架、执行引擎、设计决策
- [测试指南](docs/TESTING.md) — 四件套、用例字段、Mock、运行与排错
- [算子导航](operator_md/算子导航.md) — 52 个算子的用途、参数与取舍
- 图示：[架构与算子生命周期](docs/html/ARCHITECTURE.html)（分层、调用关系、数据流）

## 测试

```bash
python3 -m unittest discover -s tests -t .
```

当前：355 项通过（含算子用例、注册检查、catalog 与框架单测）。

## License

MIT
