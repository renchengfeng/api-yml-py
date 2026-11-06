# jsonMerge

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/jsonMerge.py` ｜ 用例：[jsonMerge_input.yaml](jsonMerge_input.yaml)

## 简介

把 patch 合并进 base；deep=true 时递归合并对象。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `base` | any | ✅ | — | ✅ | 基础对象 |
| `patch` | any | ✅ | — | ✅ | 覆盖对象 |
| `deep` | bool |  | True |  | 是否递归合并对象 |

## 输出

合并后的对象。

## 错误约束

base / patch 不是对象返回 400。

## 设计说明

通用能力，不包含 RSI 业务语义。
