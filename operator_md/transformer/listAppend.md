# listAppend

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/listAppend.py` ｜ 用例：[listAppend_input.yaml](listAppend_input.yaml)

## 简介

返回 `data + [item]`，不修改原列表。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | list | ✅ | — | ✅ | 原列表 |
| `item` | object | ✅ | — | ✅ | 追加元素 |

## 输出

新列表。
