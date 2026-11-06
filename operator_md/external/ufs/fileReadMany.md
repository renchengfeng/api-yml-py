# fileReadMany

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fileReadMany.py` ｜ 用例：[fileReadMany_input.yaml](fileReadMany_input.yaml)

## 简介

批量读取目录中的文件，按 `text / yaml / json / markdown` 解析。只返回文件内容与元信息，不做业务过滤。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `subdir` | string |  | '' | ✅ | 相对 baseDir 的子目录 |
| `suffix` | string |  | '.yaml' |  | 文件后缀，空字符串表示全部 |
| `recursive` | bool |  | False |  | 是否递归子目录 |
| `format` | string |  | 'text' |  | 读取后的解析格式 |
| `limit` | int |  | 0 |  | 最多读取条数，0 表示不限 |
| `skipInvalid` | bool |  | False |  | 解析失败时跳过该文件 |
| `exclude` | list |  | [] |  | 跳过匹配这些 glob 的相对路径 |

## 输出

`{items: [{path, data, bytes, rev}], count}`。

## 错误约束

解析失败 400；`subdir` 不是目录 400；目录不存在返回空列表。

## 设计说明

这是一个通用算子，不包含 RSI 或任何具体业务语义；由 YAML 接口组合使用。
