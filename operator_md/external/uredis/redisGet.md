# redisGet

> 分类：`external / uredis` ｜ 数据源：`kv` 类（redis）｜ 实现：`lowcode/operators/external/uredis/redisGet.py` ｜ 用例：[redisGet_input.yaml](redisGet_input.yaml)

## 简介

按键读取 Redis 并解析值。**读取方式由 `command` 决定，值的格式由 `format` 决定。**

它合并了 datamore_lite 的 `stringRedisReader`、`jsonRedisReader`、`csvRedisReader` 三个读取器。三者的差别只在值怎么解析，不必拆成三个算子。

| format | 适用的值 | 输出 |
|---|---|---|
| `raw` | 任意字符串 | 原样返回字符串，解析交给下游 |
| `json` | JSON 字面量 | 解析后的对象或列表 |
| `csv` | 分隔符字符串 | 只配 `delimiter`：单个对象；同时配 `rowDelimiter`：对象列表 |

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `dataSource` | 字符串 | | — | | Redis 数据源。不写时依次取分组的 `dataSource`、唯一的 kv 类数据源 |
| `key` | 字符串 | ✅ | — | ✅ | 键名，对应 datamore 的 `keyTemplate`，例如 `"rt\|rank\|{{ inputs.env }}"` |
| `command` | 字符串 | | `get` | | `get` / `hgetall` |
| `format` | 字符串 | | `raw` | | `raw` / `json` / `csv`；用于 `hgetall` 时作用于每个 field 的值 |
| `delimiter` | 字符串 | | `"\|"` | | CSV 列分隔符 |
| `rowDelimiter` | 字符串 | | — | | CSV 行分隔符；设置后返回对象列表 |
| `fields` | 列表 | | `[]` | | CSV 列名，按位置一一对应；`format=csv` 时必填 |
| `default` | 任意 | | — | | 键不存在（或 hash 为空）时的返回值 |

## 输入

`key` 模板可以引用 `inputs`、`request` 和上游节点输出，例如 `"rt|rank|{{ group.env }}|{{ group.id }}"`。

## 输出

```yaml
# format: json      '[{"uid":"u1","score":90}]'      → [{uid: u1, score: 90}]
# format: raw       '1|5|oXyz|1001'                   → "1|5|oXyz|1001"
# format: csv       'Alice,30,Beijing'  (delimiter ",", fields [name, age, city])
#                                                     → {name: Alice, age: "30", city: Beijing}
# format: csv       'u1,90,A;u2,80,B;'  (rowDelimiter ";", delimiter ",", fields [uid, score, tag])
#                                                     → [{uid: u1, ...}, {uid: u2, ...}]（末尾空行跳过）
# command: hgetall  {challenge_001: '{"win":"5"}'}  (format json)
#                                                     → {challenge_001: {win: "5"}}
```

- CSV 列数不足时，缺失的列补空串，保证输出总是包含 `fields` 中的全部列；
- 键不存在时返回 `default`，不报错，DAG 继续执行（沿用 datamore「空数据兜底不报错」的原则）。

## 节点示例

```yaml
- id: rank
  name: "redisGet"
  config:
    dataSource: cache
    key: "rt|rank|{{ inputs.env }}|{{ inputs.groupid }}"
    format: json
    default: []
```

## 错误约束

**启动期**：

| 场景 | 报错 |
|---|---|
| `format=csv` 但没有 `fields` | `format=csv 时 fields 必须是非空的字符串列表` |
| `delimiter` 为空，或与 `rowDelimiter` 相同 | `delimiter 不能为空，也不能与 rowDelimiter 相同` |
| `command` / `format` 取值非法 | 附近似名提示 |
| 配置了 redis 数据源但未安装 redis-py | **启动即失败**：`redis datasource requires redis-py: pip install "lowcode[redis]"` |

**运行期**：`format=json` 但值不是合法 JSON 时返回 500 `键 xxx 的值不是合法 JSON`。连接失败时返回 500，错误信息带节点前缀。

## 设计说明

- datamore 用 `output.type`（mapval/json_array…）配合 `delimiter` 的长度（1 个或 2 个字符）来隐式决定输出形态。这里改成显式的 `format` 加 `rowDelimiter`：意图写在配置里，不需要从分隔符长度去推断。
- 列名直接放在 `fields` 中，不用另外声明 `output`。
