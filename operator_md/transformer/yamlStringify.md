# yamlStringify

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/yamlStringify.py` ｜ 用例：[yamlStringify_input.yaml](yamlStringify_input.yaml)

## 简介

把对象序列化为 YAML 文本，保留插入顺序。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | any | ✅ | — | ✅ | 任意可序列化对象 |

## 输出

YAML 字符串。

## 错误约束

对象不可序列化时由框架转成 500。

## 设计说明

这是一个通用算子，不包含 RSI 或任何具体业务语义；由 YAML 接口组合使用。
