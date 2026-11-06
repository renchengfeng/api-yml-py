# jsonParse

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/jsonParse.py` ｜ 用例：[jsonParse_input.yaml](jsonParse_input.yaml)

## 简介

把 JSON 文本解析成对象。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `content` | string | ✅ | — | ✅ | JSON 文本 |

## 输出

解析后的对象。

## 错误约束

JSON 非法返回 400。

## 设计说明

通用能力，不包含 RSI 业务语义。
