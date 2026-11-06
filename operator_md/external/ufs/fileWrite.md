# fileWrite

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileWrite.py` ｜ 用例：[fileWrite_input.yaml](fileWrite_input.yaml)

## 简介

原子写入一个文本文件；可选 `expectedRev` 做乐观锁。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `path` | string | ✅ | — | ✅ | 相对 baseDir 的文件路径 |
| `content` | string | ✅ | — | ✅ | 写入内容 |
| `encoding` | string |  | 'utf-8' |  | 文本编码 |
| `atomic` | bool |  | True |  | 临时文件 + rename 原子写入 |
| `expectedRev` | string |  | '' | ✅ | 非空时校验旧文件摘要 |
| `createDirs` | bool |  | True |  | 父目录不存在时创建 |

## 输出

`{path, bytes, rev}`。

## 错误约束

目录穿越 403；`expectedRev` 不匹配 409；目标是目录 400。

## 设计说明

这是一个通用算子，不包含 RSI 或任何具体业务语义；由 YAML 接口组合使用。
