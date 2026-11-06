"""aggregate 分类：把一组数据聚合为统计结果。

对应 datamore_lite 预留的 aggregate/ 目录（未实现）。提供：
    listAgg   对对象列表的数值字段做统计（count / sum / avg / min / max）
    groupBy   按字段分组统计
"""
from . import groupBy, listAgg  # noqa: F401  导入即注册
