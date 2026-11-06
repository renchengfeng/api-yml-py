"""selector 分类：从上游数据中选择 / 投影。

对应 datamore_lite 预留的 selector/ 目录（未实现）。提供：
    fieldPicker   按声明挑选字段，缺失补 null，输出结构稳定
    renameFields  按映射重命名字段
"""
from . import fieldPicker, renameFields  # noqa: F401  导入即注册
