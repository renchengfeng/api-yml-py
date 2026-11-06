# uuid

> 分类：`transformer` ｜ 实现：`lowcode/operators/transformer/uuid.py` ｜ 用例：[uuid_input.yaml](uuid_input.yaml)

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `prefix` | string |  | 空 |  | 前缀 |
| `value` | string |  | 空 | ✅ | 固定值；为空时随机生成 |
| `length` | int |  | 12 |  | 随机 hex 长度 |
