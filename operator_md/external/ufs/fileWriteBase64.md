# fileWriteBase64

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileWriteBase64.py` ｜ 用例：[fileWriteBase64_input.yaml](fileWriteBase64_input.yaml)

## 简介

把 base64 内容解码后原子写入文件，适合二进制上传。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许写入的根目录 |
| `path` | string | ✅ | — | ✅ | 相对 baseDir 的文件路径 |
| `contentBase64` | string | ✅ | — | ✅ | base64 内容 |
| `atomic` | bool |  | True |  | 临时文件 + rename |
| `createDirs` | bool |  | True |  | 父目录不存在时创建 |

## 输出

`{path, bytes, rev}`。

## 错误约束

base64 非法 400；目录穿越 403；目标是目录 400。

## 设计说明

通用能力，不包含 RSI 业务语义。
