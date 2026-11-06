# jsonlAppend

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/jsonlAppend.py` ｜ 用例：[jsonlAppend_input.yaml](jsonlAppend_input.yaml)

## 简介

把一个对象或对象列表追加为 JSONL 行。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许写入的根目录 |
| `path` | string | ✅ | — | ✅ | 相对 baseDir 的 JSONL 文件 |
| `items` | any | ✅ | — | ✅ | 对象或对象列表 |
| `createDirs` | bool |  | True |  | 父目录不存在时创建 |

## 输出

`{path, count}`。

## 错误约束

目标目录 400；路径越界 403。

## 设计说明

通用能力，不包含 RSI 业务语义。
