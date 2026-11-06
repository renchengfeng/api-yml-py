"""external 分类：与外部系统交互（读写数据源），对应 datamore_lite 的 external/uhttp、external/uredis。

按数据源再细分为：
    usql    SQL 数据源（sqlite / mysql）
    uhttp   HTTP 上游
    uredis  Redis
"""
from . import uhttp, uredis, usql  # noqa: F401  导入即注册
