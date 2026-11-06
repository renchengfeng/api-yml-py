# textDiff

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/textDiff.py` ｜ 用例：[textDiff_input.yaml](textDiff_input.yaml)

## 简介

生成两段文本的 unified diff，只做文本比较。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `left` | string | ✅ | — | ✅ | 旧文本 |
| `right` | string | ✅ | — | ✅ | 新文本 |
| `fromfile` | string |  | 'left' | ✅ | 旧文件标题 |
| `tofile` | string |  | 'right' | ✅ | 新文件标题 |
| `context` | int |  | 3 |  | 上下文行数 |

## 输出

unified diff 字符串；相同文本为空串。

## 错误约束

context 小于 0 时启动期报错。

## 设计说明

通用能力，不包含 RSI 业务语义。
