# renameFields

> 分类：`selector` ｜ 数据源：无 ｜ 实现：`lowcode/operators/selector/renameFields.py` ｜ 用例：[renameFields_input.yaml](renameFields_input.yaml)

## 简介

按映射**重命名字段**，未列出的字段保持原名，其它一切不变。只改名字，不选字段、不转类型、不做聚合。

典型场景：`groupBy` 的统计列固定叫 `count` / `sum` / `avg`，想让 API 返回业务名字（如 `cnt`）时，用本算子在一层里改名，比在 `respBuilder` 里重建结构更直观。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | 任意 | ✅ | — | ✅ | 对象或对象列表 |
| `mapping` | 对象 | ✅ | — | | 旧字段名 → 新字段名，如 `{sum: cnt}` |

## 输入

`data` 引用上游输出；`mapping` 是静态映射（不能写模板）。

## 输出

与输入同构的新对象 / 列表：

```yaml
# mapping: {sum: cnt}
[{date: "20261103", sum: 13}]  →  [{date: "20261103", cnt: 13}]
```

| 情况 | 结果 |
|---|---|
| 字段不在 `mapping` 里 | 原样保留（含 `null`） |
| 目标字段名与已有字段冲突 | 报错，不静默覆盖 |
| `data` 不是对象 / 列表 | 报错 |
| `mapping` 为空 / 值不是字符串 / 目标重名 | **启动期**报错 |

## 节点示例

```yaml
- id: counts
  name: "renameFields"
  depends: [merged]
  config: {data: "{{ merged }}", mapping: {sum: cnt}}
```
