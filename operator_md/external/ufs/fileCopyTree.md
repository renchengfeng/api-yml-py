# fileCopyTree

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileCopyTree.py` ｜ 用例：[fileCopyTree_input.yaml](fileCopyTree_input.yaml)

## 简介

递归复制一个目录，限制文件数并拒绝符号链接。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `from` | string | ✅ | — | ✅ | 源目录相对路径 |
| `to` | string | ✅ | — | ✅ | 目标目录相对路径 |
| `overwrite` | bool |  | False |  | 目标已存在时是否覆盖 |
| `maxFiles` | int |  | 5000 |  | 最大复制文件数 |

## 输出

`{from, to, files, count, bytes}`。

## 错误约束

源目录不存在 404；目标已存在且未 overwrite 409；越界或符号链接 403；文件数超限 413。

## 设计说明

通用能力，不包含 RSI 业务语义。
