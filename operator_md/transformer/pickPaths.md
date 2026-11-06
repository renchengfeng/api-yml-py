# pickPaths

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/pickPaths.py` ｜ 用例：[pickPaths_input.yaml](pickPaths_input.yaml)

## 简介

按“输出字段 → 源路径”映射投影对象或对象列表，支持嵌套路径。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | any | ✅ | — | ✅ | 对象或对象列表 |
| `fields` | any | ✅ | — |  | 输出字段 -> 源路径，如 id: data.id |

## 输出

新对象或对象列表；缺失路径补 `null`。

## 错误约束

`fields` 为空或值不是字符串时启动期报错。

## 设计说明

这是一个通用算子，不包含 RSI 或任何具体业务语义；由 YAML 接口组合使用。
