# fileImportTree

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileImportTree.py` ｜ 用例：[fileImportTree_input.yaml](fileImportTree_input.yaml)

## 简介

把源目录导入目标目录，支持 `error / overwrite / version` 冲突策略；overwrite 会保留 backup。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `from` | string | ✅ | — | ✅ | 源目录 |
| `to` | string | ✅ | — | ✅ | 目标目录 |
| `conflict` | string |  | error | ✅ | error / overwrite / version |
| `maxFiles` | int |  | 5000 |  | 最大文件数 |

## 输出

`{from, to, backup, versioned, files}`。

## 设计说明

通用目录导入能力，不包含 Skill 业务校验。
