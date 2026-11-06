# dirList

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/dirList.py` ｜ 用例：[dirList_input.yaml](dirList_input.yaml)

## 简介

列出目录下的直接子项，可按名称前缀过滤。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `subdir` | string |  | 空 | ✅ | 相对目录 |
| `prefix` | string |  | 空 | ✅ | 名称前缀 |
| `limit` | int |  | 0 |  | 最多条数 |

## 输出

`{items: [{name, path, type, size, mtime}], count}`。
