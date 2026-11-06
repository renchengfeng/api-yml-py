# dateRange

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/dateRange.py` ｜ 用例：[dateRange_input.yaml](dateRange_input.yaml)

## 简介

把「起止日期」展开成**日期列表**（含首尾），格式由 `format` 决定。只为"按天展开"服务：不做读取、不做聚合，也不猜业务含义。

典型场景：按日期区间批量读缓存 / 查库时，先用本算子得到 `["20261103", "20261104"]`，再用 `templateMap` 拼出每天的键名，交给 `redisMGet` 一次读完。DAG 的节点数在启动期固定，**循环只能靠这种"先展开成列表"的方式表达**。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `start` | 字符串 | ✅ | — | ✅ | 起始日期（含），如 `"20261103"` |
| `end` | 字符串 | ✅ | — | ✅ | 结束日期（含），与 `start` 同格式 |
| `format` | 字符串 | | `%Y%m%d` | | 日期格式（`strftime` / `strptime`），如 `%Y-%m-%d` |
| `limit` | 整数 | | `366` | | 区间最大天数；超过直接报 400，避免下游 fan-out 爆炸 |

## 输入

`start` / `end` 是模板，通常来自入参：

```yaml
config: {start: "{{ inputs.sday }}", end: "{{ inputs.eday }}", format: "%Y%m%d"}
```

## 输出

字符串列表，按日期升序、含首尾：

```yaml
# format: "%Y%m%d"，start=20261103，end=20261105
["20261103", "20261104", "20261105"]
```

| 情况 | 结果 |
|---|---|
| `start == end` | 只有一个元素 |
| `start > end` | 400 `start ... is after end ...` |
| 日期不合法（如 `20261332`） | 400 `invalid date` |
| 天数超过 `limit` | 400 `date range too large` |
| `format` 非法（如 `%Q`） | **启动期**报错 |

## 节点示例

```yaml
- id: dates
  name: "dateRange"
  config: {start: "{{ inputs.sday }}", end: "{{ inputs.eday }}", format: "%Y%m%d", limit: 92}
```
