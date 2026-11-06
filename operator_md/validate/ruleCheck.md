# ruleCheck

> 分类：`validate` ｜ 数据源：无 ｜ 实现：`lowcode/operators/validate/ruleCheck.py` ｜ 用例：[ruleCheck_input.yaml](ruleCheck_input.yaml)

## 简介

按声明式规则校验对象；支持 `unique`、`countWhere`、`refExists`、`relatedForbidden`。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | object | ✅ | — | ✅ | 待校验对象 |
| `context` | object |  | {} | ✅ | 外部 ID 集合 |
| `rules` | list | ✅ | — | ✅ | 规则列表 |

## 输出

`{ok, errors}`。
