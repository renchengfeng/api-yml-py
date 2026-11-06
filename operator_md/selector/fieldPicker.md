# fieldPicker

> 分类：`selector` ｜ 数据源：无 ｜ 实现：`lowcode/operators/selector/fieldPicker.py` ｜ 用例：[fieldPicker_input.yaml](fieldPicker_input.yaml)

## 简介

字段投影：从对象或对象列表中**按声明挑选字段**，缺失字段补 `null`，输出结构稳定。

对应 datamore_lite 预留的 `selector/` 目录。典型用途是**裁剪响应**：SQL 查回 10 列，接口只需要 3 列，或者不同接口要复用同一个查询节点、各自暴露不同字段。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `data` | 任意 | ✅ | — | ✅ | 对象或对象列表；null 等非对象原样透传 |
| `fields` | 列表 | ✅ | — | | 保留的字段，按声明顺序输出 |

## 输入

`data` 模板引用上游节点；`fields` 是静态字段名列表。

## 输出

- 输入是对象：`{<field>: 值, ...}`，字段顺序与 `fields` 一致，**缺失字段补 `null`**（对齐 datamore csv 缺列补空串的"输出 schema 稳定"原则）；
- 输入是列表：逐行投影；
- 输入是 `null` 等非对象：原样透传；
- 空列表 → `[]`。

## 节点示例

```yaml
- id: users
  name: "sqlQuery"
  config: {sql: "select id, name, phone, level, city from users", ...}
- name: "fieldPicker"
  config:
    data: "{{ users }}"
    fields: [id, name, level]     # 只对外暴露 3 列
```

## 错误约束

**启动期**：`fields` 为空或包含非字符串元素时报错。

**运行期**：不报错。缺失字段补 `null`，非对象的行原样透传。

## 设计说明

- 与 `respBuilder` 模板手写投影相比：不用把每个字段名写两遍（模板键 + 取值表达式），且**缺失字段的行为是确定的**（补 `null`），而不是模板求值报错或需要逐个写 `default`。
- 复制后再输出，不改上游数据（测试框架会检查这一点）。
