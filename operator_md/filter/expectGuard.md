# expectGuard

> 分类：`filter` ｜ 数据源：无 ｜ 实现：`lowcode/operators/filter/expectGuard.py` ｜ 用例：[expectGuard_input.yaml](expectGuard_input.yaml)

## 简介

断言。当 `expect` 为假时中止接口，返回指定的 `code` 和 `msg`。典型用法是「查不到数据时返回 404」「余额不足时返回 400」。

它在本框架中承担 datamore_lite `paramChecker` 的「业务校验」部分。参数的非空、正则、枚举校验已经由接口的 `inputs` 声明直接完成，不需要再配节点。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `expect` | 任意 | ✅ | — | ✅ | 期望为真的条件。`null`、`false`、`0`、空串、空列表、空对象都视为假 |
| `code` | 整数 | | `400` | | 失败时的业务码。在 400~599 之间时同时作为 HTTP 状态码 |
| `msg` | 字符串 | | `校验未通过` | ✅ | 失败提示，支持模板 |

## 输入

`expect` 和 `msg` 可以引用 `inputs`、`request` 和上游节点输出。

## 输出

通过时输出 `true`（一般不会被引用）；失败时中止接口：

| code | HTTP 状态 | 响应体 |
|---|---|---|
| 400~599，例如 404 | 404 | `{"code": 404, "msg": "用户 7 不存在", "data": null}` |
| 其他，例如 1001 | 200 | `{"code": 1001, "msg": "...", "data": null}`（业务码风格） |

失败信息**不加**节点前缀：它是写给调用方看的，而不是给排查问题的人看的。

## 节点示例

```yaml
- id: user
  name: "sqlQuery"
  config: {sql: "select * from users where id = :uid", params: {uid: "{{ inputs.uid }}"}, single: true}
- name: "expectGuard"
  config:
    expect: "{{ user }}"
    code: 404
    msg: "用户 {{ inputs.uid }} 不存在"
```

## 错误约束

**启动期**：`code` 为 0（0 表示成功）时报错；`code` 不是 dynamic 字段，写模板时报错（错误码应该在配置时就确定）。

## 设计说明

- 本框架**不提供**条件分支或循环节点。`expectGuard` 加上表达式已经覆盖「前置条件不满足就返回」这类最常见的场景；更复杂的逻辑应该写成自定义算子，而不是把 YAML 变成编程语言。
