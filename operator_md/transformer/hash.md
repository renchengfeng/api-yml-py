# hash

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/hash.py` ｜ 用例：[hash_input.yaml](hash_input.yaml)

## 简介

计算文本的 SHA1 / SHA256 十六进制摘要。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `algorithm` | string |  | 'sha1' |  | 摘要算法 |
| `content` | string | ✅ | — | ✅ | 待摘要文本 |

## 输出

十六进制摘要字符串。

## 错误约束

配置错误在启动期暴露。

## 设计说明

这是一个通用算子，不包含 RSI 或任何具体业务语义；由 YAML 接口组合使用。
