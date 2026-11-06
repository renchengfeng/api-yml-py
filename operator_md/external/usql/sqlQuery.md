# sqlQuery

> 分类：`external / usql` ｜ 数据源：`sql` 类（sqlite / mysql）｜ 实现：`lowcode/operators/external/usql/sqlQuery.py` ｜ 用例：[sqlQuery_input.yaml](sqlQuery_input.yaml)

## 简介

执行查询 SQL，返回**行列表**（每行一个对象，列名为键）；`single: true` 时只返回首行。

参数**只能**通过 `:name` 绑定传入，`sql` 字段本身不接受 `{{ }}` 模板。所以无论入参是什么内容，都只会被当作值处理，不可能拼接出注入 SQL。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `dataSource` | 字符串 | | — | | SQL 数据源名。不写时依次取分组的 `dataSource`、唯一的 sql 类数据源 |
| `sql` | 字符串 | ✅ | — | | 只能是 `SELECT` / `WITH`，参数用 `:name` 绑定 |
| `params` | 对象/字符串 | | `{}` | ✅ | 绑定参数，值支持模板；入参名与绑定名一致时可整体写 `"{{ inputs }}"` |
| `single` | 布尔 | | `false` | | 只取首行：有数据返回对象，无数据返回 `null` |

## 输入

- 通过 `params` 的模板读取 `inputs`、`request` 或上游节点输出，例如 `{id: "{{ user.id }}"}`。
- 绑定名的识别会跳过引号内的字面量、注释和 `::type` 强转，所以 `':x'`、`'10:30'`、`-- :y` 都不算绑定参数。

## 输出

| 条件 | 输出 |
|---|---|
| 默认 | `[{列: 值, ...}, ...]`；没有命中时返回 `[]` |
| `single: true` | `{列: 值, ...}`；没有命中时返回 `null` |

## 节点示例

```yaml
- id: users
  name: "sqlQuery"
  config:
    dataSource: main
    sql: select id, name, level from users where level >= :level order by id
    params: {level: "{{ inputs.level }}"}
```

如果表里是 `(1,a,1) (2,b,3) (3,c,5)`，`inputs.level=3` 时输出：

```yaml
[{id: 2, name: b, level: 3}, {id: 3, name: c, level: 5}]
```

分页偏移量这类计算可以直接写在模板里：`offset: "{{ (inputs.page - 1) * inputs.size }}"`。

## 错误约束

**启动期**（服务无法启动，报错带文件和字段位置）：

| 场景 | 报错 |
|---|---|
| `sql` 里写了 `{{ }}` | `字段 sql 不支持 {{ }} 模板` |
| SQL 中的 `:x` 没有在 `params` 中提供 | `SQL 中的 :x 没有在 params 中提供` |
| `params` 中的键没有在 SQL 中用到 | `params.x 没有在 SQL 中使用`（防止名字写错后静默失效） |
| 写语句（INSERT/UPDATE/DELETE…） | `sqlQuery 只能执行 SELECT/WITH 语句…（请改用 sqlExec）` |
| 数据源不存在 / 类别不符 / 无法自动选择 | 附近似名提示或候选列表 |
| 引用了未声明的入参或非上游节点 | `引用了未声明的入参 inputs.x` / `…不是当前节点的上游` |

当 `params` 整体写成 `"{{ inputs }}"` 时，绑定参数的双向核对推迟到运行期，由数据库驱动报告缺失的参数。

**运行期**：数据库报错时返回 500，信息形如 `[users] OperationalError: no such table: nope`，错误信息带节点 id 前缀。

## 设计说明

- datamore_lite 只有 Redis 读取算子。它的旧版配置里出现过 `sql: "...'${openid}'"` 这种字符串拼接写法，这里刻意改成只允许绑定参数。
- 读写拆成 `sqlQuery` 和 `sqlExec` 两个算子，配合数据源的 `readonly` 选项，可以防止接口配置里混进写语句。
