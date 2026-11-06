# fileWriteMany

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileWriteMany.py` ｜ 用例：[fileWriteMany_input.yaml](fileWriteMany_input.yaml)

## 简介

按顺序批量写文本或 base64 文件。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许写入的根目录 |
| `files` | list | ✅ | — | ✅ | [{path, content\|contentBase64, encoding?}] |
| `atomic` | bool |  | True |  | 单文件临时文件 + rename |
| `createDirs` | bool |  | True |  | 父目录不存在时创建 |

## 输出

`{files: [{path, bytes, rev}], count, bytes}`。

## 错误约束

path 越界 403；目标目录 400；base64 非法 400。

## 设计说明

通用文件/SQL 能力，不包含 RSI 业务语义。
