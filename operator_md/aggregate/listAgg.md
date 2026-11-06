# listAgg

> 分类：`aggregate` ｜ 数据源：无 ｜ 实现：`lowcode/operators/aggregate/listAgg.py` ｜ 用例：[listAgg_input.yaml](listAgg_input.yaml)

## 简介

对对象列表的数值字段做**整体统计**，返回 `{count, sum, avg, min, max}` 中声明的项。

对应 datamore_lite 预留的 `aggregate/` 目录。典型用途是订单金额汇总、列表概览这类"查询 + 统计"仪表盘场景。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | 列表 | ✅ | — | ✅ | 对象列表 |
| `field` | 字符串 | | — | | 数值字段；`ops` 只有 count 时可省略 |
| `ops` | 列表 | | `[count, sum, avg, min, max]` | | 统计项，按声明顺序输出 |

## 输入

`data` 模板引用上游节点（通常是 `sqlQuery` / `redisGet` 的输出）。

## 输出

按 `ops` 声明输出统计对象。规则：

| 统计项 | 计算方式 |
|---|---|
| `count` | 列表行数（含数值字段缺失的行） |
| `sum` / `avg` / `min` / `max` | 只统计字段有值的行；avg 保留 4 位小数 |
| 数值字段缺失 / null 的行 | 跳过，不报错 |
| 列表为空或全部缺失 | `sum: 0`，`avg / min / max: null`（空数据兜底不报错） |

## 节点示例

```yaml
- id: orders
  name: "sqlQuery"
  depends: []
  config: {sql: "select amount, status from orders where uid = :uid", ...}
- name: "listAgg"
  depends: [orders]
  config:
    data: "{{ orders }}"
    field: amount
    ops: [count, sum, avg, max]
```

订单金额为 `[320.8, 427.16]` 时输出 `{count: 2, sum: 747.96, avg: 373.98, max: 427.16}`。

## 错误约束

**启动期**：`ops` 为空 / 含未知项 / 有重复时报错（附近似名提示）；`ops` 含 count 之外的项而未提供 `field` 时报错。

**运行期**：`data` 渲染结果不是列表时返回 500；某行的字段值是非数值（bool / 字符串）时返回 500 —— 显式报错好过静默把脏数据丢掉。

## 设计说明

- 统计在 Python 侧完成而不是塞进 SQL：同一个查询节点可以同时喂 `listAgg` 和 `groupBy`，避免为了统计多发一条 SQL。
- `count` 是列表行数，与数值字段是否缺失无关，语义是"有多少条记录"。
