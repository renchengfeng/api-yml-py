# zipExtract

> 分类：`external` ｜ 数据源：无 ｜ 实现：`lowcode/operators/external/ufs/zipExtract.py` ｜ 用例：[zipExtract_input.yaml](zipExtract_input.yaml)

## 简介

把 base64 zip 安全解压到 `baseDir/target`，限制文件数、总字节数，拒绝路径穿越与符号链接。只做解压，不解业务语义。

## Config 参数

| 参数 | 类型 | 必填 | 默认 | 模板 | 说明 |
|---|---|---|---|---|---|
| `baseDir` | string | ✅ | — |  | 允许写入的根目录 |
| `target` | string | ✅ | — | ✅ | 相对 baseDir 的目标目录 |
| `zipBase64` | string | ✅ | — | ✅ | zip 文件的 base64 |
| `maxFiles` | int |  | 2000 |  | 最大文件数 |
| `maxBytes` | int |  | 20971520 |  | 最大解压总字节数 |

## 输出

`{target, files, count, bytes}`。

## 错误约束

base64 非法 400；zip 非法 400；文件数 / 总大小超限 413；路径穿越 403。

## 设计说明

解压后是否包含 `SKILL.md`、目录结构是否合法，由调用方（RSI 领域逻辑）判断。
