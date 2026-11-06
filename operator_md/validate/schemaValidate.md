# schemaValidate

> 分类：`validate` ｜ 数据源：无 ｜ 实现：`lowcode/operators/validate/schemaValidate.py` ｜ 用例：[schemaValidate_input.yaml](schemaValidate_input.yaml)

## 简介

校验 JSON Schema 子集：type、required、properties、items、enum、pattern、长度、数值范围。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | any | ✅ | — | ✅ | 待校验数据 |
| `schema` | any | ✅ | — |  | JSON Schema 子集 |

## 输出

`{ok, errors: [{path, message}]}`。

## 错误约束

校验失败不抛异常，返回 `ok=false`。

## 设计说明

通用能力，不包含 RSI 业务语义。
