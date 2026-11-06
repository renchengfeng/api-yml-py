# numberCast

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/numberCast.py` ｜ 用例：[numberCast_input.yaml](numberCast_input.yaml)

## 简介

把指定字段的**字符串值转成数值**（整数优先，否则浮点），其它字段原样保留。输出新的对象 / 列表，不改动上游输出。

典型场景：`redisGet` 用 `format: csv` 解析 `date|cnt` 后，`cnt` 是字符串；`groupBy` / `listAgg` 的数值统计明确拒绝字符串，先用本算子转换即可。职责单一：只做类型转换，不做读取、投影或聚合。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | 任意 | ✅ | — | ✅ | 对象或对象列表，通常是上游节点输出 |
| `fields` | 列表 | ✅ | — | | 要转成数值的字段名；其它字段原样保留 |

## 输入

`data` 模板引用上游节点。值为对象时逐字段处理一次；值为列表时逐行处理。

## 输出

与输入同构的新对象 / 列表：

```yaml
# fields: [cnt]
[{date: "2026-11-04", cnt: "10"}, {date: "2026-11-05", cnt: "2.5"}]
→ [{date: "2026-11-04", cnt: 10}, {date: "2026-11-05", cnt: 2.5}]
```

| 原值 | 结果 |
|---|---|
| `"10"` / `"2.5"` | `10` / `2.5` |
| 数值、`bool` | 原样保留 |
| `null` / 字段缺失 | 原样保留，不补 0 |
| `"abc"`、`""` 等非数字字符串 | 报错 |

## 节点示例

```yaml
- name: "numberCast"
  depends: [rows]
  config:
    data: "{{ rows }}"
    fields: [cnt]
```

## 错误约束

**启动期**：`fields` 为空或含非字符串 → `fields must be a non-empty list of strings`。

**运行期**：`data` 不是对象 / 列表 → `data must render to an object or a list`；行不是对象 → `rows to cast must be objects`；字段值不是字符串或不能解析为数字 → `value ... of field ... is not a number`。

## 设计说明

- 与 `aggregate/stats.py::numbers()` 保持一致的取向：显式报错好过静默丢数，所以不把 `""` 当成 0，也不猜测数字格式；
- 不原地修改 `args` 与上游输出（节点间共享），每行都新建 dict；
- 与 `fieldPicker` 互补：一个选字段，一个转类型，两者都不做聚合。
