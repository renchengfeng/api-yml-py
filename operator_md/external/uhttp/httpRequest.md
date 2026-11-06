# httpRequest

> 分类：`external / uhttp` ｜ 数据源：`http` 类（`url` 为绝对地址时可以不配）｜ 实现：`lowcode/operators/external/uhttp/httpRequest.py` ｜ 用例：[httpRequest_input.yaml](httpRequest_input.yaml)

## 简介

调用上游 HTTP 接口。JSON 响应会自动解析为对象，其他类型的响应原样返回文本。

数据源提供 `baseUrl`、公共请求头和默认超时；节点只需描述本次请求本身。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `dataSource` | 字符串 | | — | | HTTP 数据源。`url` 是相对路径时必须有（可以自动选择唯一的 http 数据源） |
| `url` | 字符串 | ✅ | — | ✅ | 相对 `baseUrl` 的路径，或 `http(s)://` 开头的绝对地址 |
| `method` | 字符串 | | `GET` | | `GET` / `POST` / `PUT` / `DELETE` / `PATCH` |
| `query` | 对象 | | `{}` | ✅ | 查询参数；值为 `null` 的项不发送（便于处理可选参数） |
| `headers` | 对象 | | `{}` | ✅ | 本次请求头，与数据源的公共 `headers` 合并（同名时以本次为准） |
| `json` | 任意 | | — | ✅ | JSON 请求体，会自动带上 `Content-Type: application/json` |
| `timeout` | 数字 | | — | | 超时秒数，不写时取数据源配置；**不会超过接口剩余时间** |

## 输入

`url`、`query`、`headers`、`json` 都可以引用 `inputs`、`request` 和上游节点输出。透传链路 id 的写法：`headers: {X-Request-Id: "{{ request.traceId }}"}`。

## 输出

- 响应头 `Content-Type` 含 `json` 时，输出为解析后的对象或列表；
- 其他情况输出响应文本（字符串）。

## 节点示例

```yaml
- id: profile
  name: "httpRequest"
  config:
    dataSource: up
    url: "/users/{{ inputs.uid }}"
    query: {fields: basic, lang: "{{ inputs.lang }}"}     # lang 为 null 时不发送
- name: "respBuilder"
  config:
    data: {name: "{{ profile.name }}"}
```

## 错误约束

**启动期**：

| 场景 | 报错 |
|---|---|
| 相对 `url` 却没有可用的 http 数据源 | `无法自动选择 http 类数据源` |
| `dataSource` 指向非 http 类数据源 | `这里需要 http 类` |
| `method` 非法 | 附近似名提示，例如 `是不是想写 'GET'？` |

**运行期**：

| 场景 | 结果 |
|---|---|
| 上游返回非 2xx | **502** `[profile] 上游返回 HTTP 500：GET … → <响应片段>` |
| 上游不可达 | **502** `上游不可达` |
| 超时（自身 timeout，或接口剩余时间耗尽） | **504** `上游超时` |

## 设计说明

- 超时取「节点或数据源的 timeout」与「接口剩余时间」中较小的一个。这样可以避免接口整体已经超时、却还在等待上游的情况。
- 只使用标准库 `urllib`，没有额外依赖。如果需要连接复用或重试，可以用插件注册新的 http 类数据源替换它。
