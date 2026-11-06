# timestamp

> 分类：`transformer` ｜ 实现：`lowcode/operators/transformer/timestamp.py` ｜ 用例：[timestamp_input.yaml](timestamp_input.yaml)

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `format` | string |  | `%Y-%m-%dT%H:%M:%S` |  | strftime 格式 |
| `value` | string |  | 空 | ✅ | 固定值；为空时取当前时间 |
