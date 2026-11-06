"""external 分类：与外部系统交互，按系统分 usql / uhttp / uredis / ufs。"""
from . import ufs, uhttp, uredis, usql  # noqa: F401  导入即注册
