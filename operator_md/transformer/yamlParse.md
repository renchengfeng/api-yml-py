# yamlParse

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/yamlParse.py` ｜ 用例：[yamlParse_input.yaml](yamlParse_input.yaml)

## 简介

把 YAML 文本解析成对象，只做解析，不判断业务字段。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `content` | string | ✅ | — | ✅ | YAML 文本 |

## 输出

YAML 对应的 Python 对象。

## 错误约束

YAML 非法返回 400。

## 设计说明

这是一个通用算子，不包含 RSI 或任何具体业务语义；由 YAML 接口组合使用。
