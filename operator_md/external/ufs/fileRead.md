# fileRead

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileRead.py` ｜ 用例：[fileRead_input.yaml](fileRead_input.yaml)

## 简介

读取一个文本文件，返回内容、字节数和摘要 rev。路径必须位于 `baseDir` 内。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `path` | string | ✅ | — | ✅ | 相对 baseDir 的文件路径 |
| `encoding` | string |  | 'utf-8' |  | 文本编码 |
| `maxBytes` | int |  | 2097152 |  | 允许读取的最大字节数 |

## 输出

`{path, content, bytes, rev}`。

## 错误约束

文件不存在 404；超过 `maxBytes` 413；目录穿越 403。

## 设计说明

这是一个通用算子，不包含 RSI 或任何具体业务语义；由 YAML 接口组合使用。
