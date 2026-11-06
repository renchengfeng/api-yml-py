# rowFilter

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/rowFilter.py` ｜ 用例：[rowFilter_input.yaml](rowFilter_input.yaml)

## 简介

按**单个字段与阈值的比较结果**保留对象列表中的行，输出新列表。条件不满足的行被丢掉，接口不中断、不报错。

与 `guard` 的区别：`guard` 是断言（不满足就中止整个接口并返回错误码），`rowFilter` 只是筛选数据。与 `fieldPicker` 的区别：一个筛行，一个选列。职责单一：只做比较与筛选，不做类型转换（交给 `numberCast`）、不做聚合（交给 `groupBy`）。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | 列表 | ✅ | — | ✅ | 对象列表，通常是上游节点输出 |
| `field` | 字符串 | ✅ | — | | 参与比较的字段；缺失或为 null 的行不保留 |
| `op` | 字符串 | | `gt` | | 比较运算符：`gt` / `gte` / `lt` / `lte` / `eq` / `ne` |
| `value` | 任意 | ✅ | — | ✅ | 阈值，支持 `{{ }}` 引用入参 |

## 输入

`data` 与 `value` 都支持模板。典型用法是把 `groupBy` 的统计结果按入参阈值过滤：

```yaml
- id: filtered
  name: "rowFilter"
  depends: [grouped]
  config: {data: "{{ grouped }}", field: sum, op: gt, value: "{{ inputs.cnt }}"}
```

## 输出

同结构的对象列表（新列表，行对象不改动）：

```yaml
# field: sum, op: gt, value: 10
[{date: d1, sum: 15}, {date: d2, sum: 10}, {date: d3, sum: 3}]
→ [{date: d1, sum: 15}]
```

| 场景 | 结果 |
|---|---|
| 缺失字段 / 字段为 `null` | 该行不保留 |
| 空列表 | 空列表 |
| 字符串与数值混比 | 报错（先用 `numberCast` 转类型） |

## 节点示例

```yaml
- name: "rowFilter"
  depends: [rows]
  config:
    data: "{{ rows }}"
    field: sum
    op: gt
    value: 10
```

## 错误约束

**启动期**：`op` 不在六个取值内 → `invalid value`。

**运行期**：`data` 不是列表 → `data must render to a list`；行不是对象 → `rows to filter must be objects`；两侧类型不可比较 → `cannot compare field ... with value ...`。

## 设计说明

- 比较函数来自标准库 `operator`，六种运算符只是同一个「按条件筛行」功能的参数；
- 不原地修改 `args` 与上游输出（节点间共享），只返回新列表；
- 不做隐式类型转换：显示报错好过把 `"15"` 和 `10` 悄悄按字符串比较。
