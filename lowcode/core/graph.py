"""节点依赖图（DAG）：拓扑分层、环检测、祖先查询。只关心 id 与依赖，不关心算子。"""
from __future__ import annotations

from typing import Dict, List, Sequence, Set

from ..errors import ConfigError


class Graph:
    def __init__(self, depends: Dict[str, Sequence[str]], where: str = ""):
        """depends: 节点 id → 上游 id 列表（dict 插入顺序 = 定义顺序）。"""
        self.depends = {n: list(d) for n, d in depends.items()}
        self.where = where
        self._ancestors: Dict[str, Set[str]] = {}

    def levels(self) -> List[List[str]]:
        """Kahn 拓扑分层：第 k 层 = 所有依赖都落在前 k-1 层的节点。

        同层节点互不依赖，可以并行；层内保持定义顺序，保证执行与报错顺序稳定。
        """
        placed: Set[str] = set()
        remaining = dict(self.depends)
        result: List[List[str]] = []
        while remaining:
            ready = [n for n, deps in remaining.items() if all(d in placed for d in deps)]
            if not ready:
                raise ConfigError(f"circular dependency: {', '.join(remaining)}", self.where)
            result.append(ready)
            placed.update(ready)
            for n in ready:
                del remaining[n]
        return result

    def ancestors(self, node: str) -> Set[str]:
        """node 的全部（直接 + 间接）上游。须在 levels() 校验无环之后调用。"""
        if node not in self._ancestors:
            acc: Set[str] = set()
            for dep in self.depends[node]:
                acc.add(dep)
                acc |= self.ancestors(dep)
            self._ancestors[node] = acc
        return self._ancestors[node]
