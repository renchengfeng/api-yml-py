# hashTree

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/hashTree.py` ｜ 用例：[hashTree_input.yaml](hashTree_input.yaml)

## 简介

计算目录树的 sha1、文件数、字节数和目录 mtime；拒绝符号链接。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `path` | string | ✅ | — | ✅ | 目录相对路径 |

## 输出

`{path, hash, files, bytes, mtime}`。

## 设计说明

用于版本快照摘要，不包含业务语义。
