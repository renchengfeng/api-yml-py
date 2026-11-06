# sqlExec

> 分类：`external / usql` ｜ 数据源：`sql` 类（sqlite / mysql）｜ 实现：`lowcode/operators/external/usql/sqlExec.py` ｜ 用例：[sqlExec_input.yaml](sqlExec_input.yaml)

## 简介

在事务中执行一条写 SQL（INSERT / UPDATE / DELETE / REPLACE），返回影响行数和新行 id。执行成功时提交，出现异常时回滚。

参数规则与 [sqlQuery](sqlQuery.md) 完全相同：只能用 `:name` 绑定，`sql` 不接受模板。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `dataSource` | 字符串 | | — | | SQL 数据源名。不写时依次取分组的 `dataSource`、唯一的 sql 类数据源 |
| `sql` | 字符串 | ✅ | — | | 只能是 `INSERT` / `UPDATE` / `DELETE` / `REPLACE`，参数用 `:name` 绑定 |
| `params` | 对象/字符串 | | `{}` | ✅ | 绑定参数，值支持模板；也可以整体写 `"{{ inputs }}"` |

## 输入

通过 `params` 的模板读取 `inputs`、`request` 或上游节点输出。

## 输出

```yaml
{rowcount: 1, lastrowid: 4}     # INSERT
{rowcount: 2, lastrowid: null}  # UPDATE / DELETE：lastrowid 固定为 null
```

`lastrowid` 只对 INSERT 有意义。不同 Python 版本或驱动在非 INSERT 语句后会返回 `None` 或 `0`，框架统一为 `null`，保证结果可预期。

## 节点示例

```yaml
- id: insert
  name: "sqlExec"
  config:
    sql: insert into users(name, phone, level) values (:name, :phone, :level)
    params: "{{ inputs }}"
- name: "respBuilder"
  config:
    data: {id: "{{ insert.lastrowid }}"}
```

## 错误约束

**启动期**：与 sqlQuery 相同。此外，写成 SELECT 语句时报 `请改用 sqlQuery`。

**运行期**：

| 场景 | 结果 |
|---|---|
| 违反约束（NOT NULL / UNIQUE…） | 500 `[insert] IntegrityError: …`，事务回滚 |
| 数据源配置了 `readonly: true` | 500 `… readonly …`，写入被拒绝 |
| 没有命中任何行 | 不报错，`rowcount: 0` |

## 设计说明

- 要防止误写库，可以对数据源设置 `readonly: true`。sqlite 会以 `mode=ro` 打开，即使配置里写了写语句，也无法执行。
- 没有提供批量写入、多语句事务这类能力。这类需求涉及幂等和补偿语义，应该写成自定义算子。
