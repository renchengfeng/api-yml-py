# fsTransaction

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/fsTransaction.py` ｜ 用例：[fsTransaction_input.yaml](fsTransaction_input.yaml)

## 简介

执行一组文件操作；失败时按逆序恢复已处理目标。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许访问的根目录 |
| `operations` | list | ✅ | — | ✅ | 文件操作列表 |

## 输出

`{committed, operations}`。

## 错误约束

非法操作 400；路径越界 403；目标/源类型错误 400；失败时自动补偿。

## 设计说明

通用文件/SQL 能力，不包含 RSI 业务语义。
