# fileCopy

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileCopy.py` ｜ 用例：[fileCopy_input.yaml](fileCopy_input.yaml)

## 简介

复制一个文件；默认不覆盖已有目标。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `from` | string | ✅ | — | ✅ | 源文件相对路径 |
| `to` | string | ✅ | — | ✅ | 目标文件相对路径 |
| `overwrite` | bool |  | False |  | 目标存在时是否覆盖 |

## 输出

`{from, to, bytes, rev}`。

## 错误约束

源文件不存在 404；目标已存在 409；目标是目录 400。

## 设计说明

这是一个通用算子，不包含 RSI 或任何具体业务语义；由 YAML 接口组合使用。
