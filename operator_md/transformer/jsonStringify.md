# jsonStringify

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/jsonStringify.py` ｜ 用例：[jsonStringify_input.yaml](jsonStringify_input.yaml)

## 简介

把对象序列化为 JSON 文本。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | any | ✅ | — | ✅ | 任意可序列化对象 |
| `indent` | int |  | 0 |  | 缩进空格数，0 表示紧凑 |

## 输出

JSON 字符串。

## 错误约束

对象不可序列化时由执行器报错。

## 设计说明

通用能力，不包含 RSI 业务语义。
