# fileExists

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileExists.py` ｜ 用例：[fileExists_input.yaml](fileExists_input.yaml)

## 简介

判断文件或目录是否存在，不抛 404。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `path` | string | ✅ | — | ✅ | 相对路径 |

## 输出

`{exists, type, path}`。

## 错误约束

路径越界 403。

## 设计说明

通用能力，不包含 RSI 业务语义。
