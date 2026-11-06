# graphCheck

> 分类：`validate` ｜ 数据源：无 ｜ 实现：`lowcode/operators/validate/graphCheck.py` ｜ 用例：[graphCheck_input.yaml](graphCheck_input.yaml)

## 简介

校验节点唯一、边端点存在、可选无环。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `nodes` | list | ✅ | — | ✅ | 节点列表 |
| `edges` | list | ✅ | — | ✅ | 边列表 |
| `idField` | string |  | 'id' |  | 节点 id 字段 |
| `fromField` | string |  | 'from' |  | 边起点字段 |
| `toField` | string |  | 'to' |  | 边终点字段 |
| `allowCycles` | bool |  | False |  | 是否允许环 |

## 输出

`{ok, errors, nodeCount, edgeCount}`。

## 错误约束

校验失败不抛异常，返回 `ok=false`。

## 设计说明

通用能力，不包含 RSI 业务语义。
