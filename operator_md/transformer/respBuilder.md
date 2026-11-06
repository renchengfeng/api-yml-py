# respBuilder

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/respBuilder.py` ｜ 用例：[respBuilder_input.yaml](respBuilder_input.yaml)

## 简介

按模板组装输出结构。通常作为接口的**最后一个节点**，决定响应 `data` 的形状。

它同时覆盖了 datamore_lite 的两个算子：

| datamore_lite | 本框架写法 |
|---|---|
| `respBuilder`（透传单个上游） | `data: "{{ rows }}"` |
| `respMergeBuilder`（`fields` 与 `depends` 按位置一一对应地合并） | `data: {rank: "{{ rank }}", score: "{{ score }}"}`，按名字合并，不依赖位置 |

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | 任意 | ✅ | — | ✅ | 任意嵌套的 dict / list / 标量，其中的字符串值支持模板 |

## 输入

模板可以引用 `inputs`、`request` 和**所有上游节点**的输出。引用的节点必须在 `depends` 链上，否则启动报错。

## 输出

模板渲染后的结构，规则如下：

| 写法 | 结果 |
|---|---|
| `"{{ inputs.page }}"` | 整串只有一个表达式时**保留原生类型**（int、list、dict 不变） |
| `"第 {{ inputs.page }} 页"` | 与文字混排时渲染成字符串 |
| `"{{ (inputs.page - 1) * inputs.size }}"` | 支持表达式（Jinja2 沙箱） |
| `"{{ rows \| length }}"`、`"{{ rows.0.id }}"` | 过滤器、列表下标 |
| `"{{ row.items }}"` | 字典**优先按键取值**（取名为 items 的列，而不是 dict.items 方法） |
| `"{{ user.age \| default(0) }}"` | 取值失败默认**报错**；需要兜底时显式写 `default` |
| `{ok: true}` | 不含模板的值在启动时就确定，请求时不再渲染 |

## 节点示例

```yaml
- name: "respBuilder"
  depends: [total, masked]
  config:
    data:
      page: "{{ inputs.page }}"
      total: "{{ total.n }}"
      list: "{{ masked }}"
```

## 错误约束

**启动期**：引用了非上游节点（`…不是当前节点的上游：请把它加入 depends`）、未知变量、未声明的入参、模板语法错误、没有写 `data`。

**运行期**：取值失败（字段不存在）时返回 500 `模板取值失败 {{ total.nope }}：值不存在（可用 | default(...) 兜底）`。

## 设计说明

- 取值失败直接报错，而不是返回空串：字段名写错能立刻发现。datamore 的 Go template 在这种情况下会渲染出 `<no value>`，问题会被悄悄带进响应里。
- 沙箱禁止访问 `__class__` 这类内部属性，配置无法借模板执行任意代码。
