# sortList

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/sortList.py` ｜ 用例：[sortList_input.yaml](sortList_input.yaml)

## 简介

按点号路径排序对象列表，支持缺失值位置。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | list | ✅ | — | ✅ | 对象列表 |
| `field` | string | ✅ | — |  | 排序字段，支持 data.updated_at |
| `desc` | bool |  | False |  | 是否降序 |
| `missing` | string |  | 'last' |  | 缺失值位置 |

## 输出

排序后的新列表，不修改上游。

## 错误约束

`field` 为空时启动期报错；不可比较值按字符串兜底。

## 设计说明

这是一个通用算子，不包含 RSI 或任何具体业务语义；由 YAML 接口组合使用。
