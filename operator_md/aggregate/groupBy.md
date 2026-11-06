# groupBy

> 分类：`aggregate` ｜ 数据源：无 ｜ 实现：`lowcode/operators/aggregate/groupBy.py` ｜ 用例：[groupBy_input.yaml](groupBy_input.yaml)

## 简介

按字段**分组统计**：组内做 count / sum / avg / min / max，输出每个组的统计行。

对应 datamore_lite 预留的 `aggregate/` 目录。典型用途是按状态、按日期、按分类的分布统计。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | 列表 | ✅ | — | ✅ | 对象列表 |
| `by` | 字符串 | ✅ | — | | 分组字段；缺失该字段的行归入 null 组 |
| `field` | 字符串 | | — | | 数值字段；`ops` 只有 count 时可省略 |
| `ops` | 列表 | | `["count"]` | | 组内统计项，按声明顺序输出 |

## 输入

`data` 模板引用上游节点（通常是 `sqlQuery` / `redisGet` 的输出）。

## 输出

对象列表，每行一个分组：

```yaml
# data 按 status 分组，ops: [count, sum]，field: amount
- {status: null,  count: 1, sum: 0}     # 缺失 status 的行归入 null 组（排最前）
- {status: paid,  count: 3, sum: 1104.8}
- {status: refunded, count: 1, sum: 50}
```

- **按 key 升序**输出（null 组最前）。datamore_lite 的白盒报告指出 map 遍历顺序随机会导致结果不稳定，这里固定排序；
- 组内统计规则与 [listAgg](listAgg.md) 相同：count 是组内行数，数值统计跳过缺失行，空组概念不存在（有组必有行）。

## 节点示例

```yaml
- id: orders
  name: "sqlQuery"
  depends: []
  config: {sql: "select amount, status from orders where uid = :uid", ...}
- name: "groupBy"
  depends: [orders]
  config:
    data: "{{ orders }}"
    by: status
    field: amount
    ops: [count, sum]
```

## 错误约束

**启动期**：与 [listAgg](listAgg.md) 相同（`ops` 校验、`field` 必填规则）。

**运行期**：`data` 渲染结果不是列表、或某行的字段值是非数值时返回 500。

## 设计说明

- 输出行的第一列直接用 `by` 字段名命名。若 `by` 恰好叫 `count` 会与统计列重名 —— 换个分组字段名即可。
- 分组 key 用原始值（不转字符串），配合 `null` 组语义，方便下游模板按 key 取值。
