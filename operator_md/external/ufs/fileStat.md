# fileStat

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileStat.py` ｜ 用例：[fileStat_input.yaml](fileStat_input.yaml)

## 简介

读取路径类型、大小、修改时间与摘要。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `path` | string | ✅ | — | ✅ | 相对路径 |
| `missingOk` | bool |  | False |  | 不存在时返回 exists=false |

## 输出

`{exists, path, type, size, mtime, rev}`。

## 错误约束

不存在且 missingOk=false 返回 404；路径越界 403。

## 设计说明

通用能力，不包含 RSI 业务语义。
