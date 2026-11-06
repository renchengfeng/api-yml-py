# redisMGet

> 分类：`external / uredis` ｜ 数据源：`kv` 类（redis）｜ 实现：`lowcode/operators/external/uredis/redisMGet.py` ｜ 用例：[redisMGet_input.yaml](redisMGet_input.yaml)

## 简介

**一次读取多个键**（Redis `MGET`），把每个键的解析结果按键顺序拼成一个列表。值的解析规则与 [redisGet](redisGet.md) 完全一致（`raw` / `json` / `csv`，共用同一份实现）。

和 `redisGet` 的分工：`redisGet` 读一个键；`redisMGet` 读一批键。需要"按日期 / 按 id 批量取"时，先用 `dateRange` 或 `templateMap` 生成键列表，再用本算子一次读完，避免每键一个节点。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `dataSource` | 字符串 | | — | | Redis 数据源。不写时依次取分组的 `dataSource`、唯一的 kv 类数据源 |
| `keys` | 列表 | ✅ | — | ✅ | 键名列表；可用列表拼接，如 `"{{ keysA + keysB }}"` |
| `format` | 字符串 | | `raw` | | `raw` / `json` / `csv` |
| `delimiter` | 字符串 | | `"\|"` | | CSV 列分隔符 |
| `rowDelimiter` | 字符串 | | — | | CSV 行分隔符；设置后每个键展开成多行 |
| `fields` | 列表 | | `[]` | | CSV 列名，按位置一一对应；`format=csv` 时必填 |
| `skipMissing` | 布尔 | | `true` | | 键不存在时跳过；`false` 时用 `default` 占位 |
| `default` | 任意 | | — | | `skipMissing=false` 时，键不存在的占位值 |

## 输入

`keys` 是模板，通常来自上游：

```yaml
config:
  keys: "{{ keysA + keysB }}"   # 两个 templateMap 的列表拼接
```

## 输出

列表。每个键的解析结果按 `keys` 的顺序拼接，**列表型结果会被展开**（`csv` + `rowDelimiter` 的多行、`json` 的数组），所以输出永远是一维列表，可以直接喂给 `numberCast` / `groupBy`：

```yaml
# keys: ["counter|daily|a|20261103", "counter|daily|b|20261103"]
# format: csv, fields: [date, cnt]
[{date: "20261103", cnt: "6"}, {date: "20261103", cnt: "7"}]
```

| 情况 | 结果 |
|---|---|
| `keys: []` | `[]`，不访问 Redis |
| 某个键不存在 | 默认跳过；`skipMissing: false` 时放入 `default` |
| `json` 值不合法 | 报错（带键名） |
| `keys` 渲染后不是字符串列表 | 报错 |
| `format: csv` 但 `fields` 为空 | **启动期**报错 |

## 节点示例

```yaml
- id: rows
  name: "redisMGet"
  depends: [keysA, keysB]
  config:
    dataSource: "redis1"
    keys: "{{ keysA + keysB }}"
    format: csv
    fields: [date, cnt]
    skipMissing: true
```
