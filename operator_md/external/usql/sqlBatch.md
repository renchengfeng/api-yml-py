# sqlBatch

> 分类：`external` ｜ 数据源：sql ｜ 实现：`lowcode/operators/external/sqlBatch.py` ｜ 用例：[sqlBatch_input.yaml](sqlBatch_input.yaml)

## 简介

在同一个 SQL 事务中执行多条写语句。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `dataSource` | string |  | — |  | SQL 数据源名 |
| `statements` | list | ✅ | — | ✅ | [{sql: ..., params: {...}}] |

## 输出

`{results: [{rowcount, lastrowid}]}`。

## 错误约束

语句必须是 INSERT / UPDATE / DELETE / REPLACE；任一失败整体回滚。

## 设计说明

通用文件/SQL 能力，不包含 RSI 业务语义。
