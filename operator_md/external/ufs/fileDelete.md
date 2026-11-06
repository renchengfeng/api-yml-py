# fileDelete

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileDelete.py` ｜ 用例：[fileDelete_input.yaml](fileDelete_input.yaml)

## 简介

删除一个文件；默认文件不存在时报错。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `path` | string | ✅ | — | ✅ | 相对 baseDir 的文件路径 |
| `missingOk` | bool |  | False |  | 文件不存在时是否视为成功 |

## 输出

`{path, deleted}`。

## 错误约束

文件不存在 404（`missingOk=true` 时返回 `deleted=false`）；拒绝删除目录 400。

## 设计说明

这是一个通用算子，不包含 RSI 或任何具体业务语义；由 YAML 接口组合使用。
