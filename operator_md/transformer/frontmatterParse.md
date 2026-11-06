# frontmatterParse

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/frontmatterParse.py` ｜ 用例：[frontmatterParse_input.yaml](frontmatterParse_input.yaml)

## 简介

解析 Markdown / SKILL.md 的 frontmatter，返回 meta 与 body。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `content` | string | ✅ | — | ✅ | 带 frontmatter 的文本 |

## 输出

`{meta, body}`。

## 错误约束

frontmatter 未闭合或 YAML 非法返回 400。

## 设计说明

这是一个通用算子，不包含 RSI 或任何具体业务语义；由 YAML 接口组合使用。
