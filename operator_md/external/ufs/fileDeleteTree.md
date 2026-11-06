# fileDeleteTree

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileDeleteTree.py` ｜ 用例：[fileDeleteTree_input.yaml](fileDeleteTree_input.yaml)

## 简介

递归删除目录，拒绝删除 baseDir 本身。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `path` | string | ✅ | — | ✅ | 目录相对路径 |
| `missingOk` | bool |  | False |  | 不存在时是否成功 |

## 输出

`{path, deleted}`。
