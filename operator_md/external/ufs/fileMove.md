# fileMove

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileMove.py` ｜ 用例：[fileMove_input.yaml](fileMove_input.yaml)

## 简介

移动一个普通文件，默认不覆盖目标。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `from` | string | ✅ | — | ✅ | 源文件 |
| `to` | string | ✅ | — | ✅ | 目标文件 |
| `overwrite` | bool |  | False |  | 目标存在时是否覆盖 |

## 输出

`{from, to}`。

## 错误约束

源不存在 404；目标存在 409；目标目录 400。

## 设计说明

通用能力，不包含 RSI 业务语义。
