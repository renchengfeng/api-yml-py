# pickValue

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/selector/pickValue.py` ｜ 用例：[pickValue_input.yaml](pickValue_input.yaml)

## 简介

根据布尔条件选择一个值；不执行子图。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `condition` | bool | ✅ | — | ✅ | 条件 |
| `whenTrue` | any |  | — | ✅ | 条件为真时的值 |
| `whenFalse` | any |  | — | ✅ | 条件为假时的值 |

## 输出

whenTrue 或 whenFalse。

## 错误约束

condition 不是布尔时由模板渲染报错。

## 设计说明

通用能力，不包含 RSI 业务语义。
