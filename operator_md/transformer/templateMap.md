# templateMap

> 分类：`transformer` ｜ 数据源：无 ｜ 实现：`lowcode/operators/transformer/templateMap.py` ｜ 用例：[templateMap_input.yaml](templateMap_input.yaml)

## 简介

把一个列表按模板**逐项渲染**成新列表。作用域里额外提供 `item`（当前元素）与 `index`（下标），其余变量（`inputs` / `request` / 上游节点输出）与普通模板一致。

它只做"列表 → 列表"的映射，不读数据、不过滤、不聚合。典型用途是把日期列表拼成一批 key / URL / SQL 参数，再交给 `redisMGet`、`httpRequest` 之类的批量算子。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `items` | 列表 | ✅ | — | ✅ | 待映射的列表，通常是上游节点输出 |
| `template` | 字符串 | ✅ | — | 自渲染 | 逐项渲染的模板，可用 `{{ item }}` / `{{ index }}` |

> `template` 是**算子自渲染**字段：框架不预编译它，因此里面可以写 `{{ item }}`；引用错误在实际渲染该项时才报。

## 输入

`items` 可以是字面量列表，也可以引用上游节点：

```yaml
config:
  items: "{{ dates }}"
  template: "counter|daily|a|{{ item }}"
```

## 输出

与输入等长的新列表；`item` 是数字 / 对象时按原生类型参与渲染：

```yaml
# items: ["20261103", "20261104"]
["counter|daily|a|20261103", "counter|daily|a|20261104"]

# items: [1, 2]，template: "n={{ item }}"
["n=1", "n=2"]
```

| 情况 | 结果 |
|---|---|
| `items: []` | `[]` |
| `items` 渲染后不是列表 | 报错 `items must render to a list` |
| `template` 语法错误 | **启动期**报错 |
| 模板引用了不存在的字段 | 运行期报错 `template lookup failed`（可用 `| default(...)` 兜底） |

## 节点示例

```yaml
- id: keysA
  name: "templateMap"
  depends: [dates]
  config: {items: "{{ dates }}", template: "counter|daily|a|{{ item }}"}
```
