# fileSwapTree

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileSwapTree.py` ｜ 用例：[fileSwapTree_input.yaml](fileSwapTree_input.yaml)

## 简介

用一个目录 rename 替换另一个目录，已有目标移到 backup。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `from` | string | ✅ | — | ✅ | 源目录，交换后会被移走 |
| `to` | string | ✅ | — | ✅ | 目标目录 |
| `maxFiles` | int |  | 5000 |  | 最大文件数 |

## 输出

`{from, to, backup}`。

## 错误约束

源目录不存在 404；目标不是目录 400；文件数超限 413；符号链接 403。

## 设计说明

通用文件/SQL 能力，不包含 RSI 业务语义。
