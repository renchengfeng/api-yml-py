"""配置层：YAML → 静态模型（*Def）。只做结构校验，不认识算子与数据源。"""
from .loader import SERVER_FILE, load_config
from .models import ApiDef, GroupDef, InputDef, NodeDef, ServerDef

__all__ = ["load_config", "SERVER_FILE",
           "ServerDef", "GroupDef", "ApiDef", "NodeDef", "InputDef"]
