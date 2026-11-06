"""命令行入口。

    python -m lowcode serve     -c conf     启动服务
    python -m lowcode check     -c conf     只校验配置，打印路由表（适合放进 CI）
    python -m lowcode explain   -c conf     解释接口：入参、每个节点在做什么、响应结构
    python -m lowcode operators                      列出已注册算子及其 config 字段
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .core.builder import response_shape
from .errors import ConfigError
from .operators import list_operators  # 导入即完成内置算子注册
from .runtime import build_runtime


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lowcode", description="YAML 驱动的低代码 HTTP 框架")
    sub = parser.add_subparsers(dest="cmd", required=True)

    serve = sub.add_parser("serve", help="启动服务（开发服务器；生产建议 gunicorn）")
    serve.add_argument("-c", "--conf", default="conf", help="配置目录（含 server.yaml），默认 ./conf")
    serve.add_argument("--host", help="覆盖 server.host")
    serve.add_argument("--port", type=int, help="覆盖 server.port")

    check = sub.add_parser("check", help="只校验配置并打印路由表")
    check.add_argument("-c", "--conf", default="conf")

    explain = sub.add_parser("explain", help="解释接口：入参、DAG 各节点在做什么、响应结构")
    explain.add_argument("-c", "--conf", default="conf")
    explain.add_argument("api", nargs="?", help="接口路径片段，如 user/list；缺省解释全部接口")

    sub.add_parser("operators", help="列出已注册的算子及其 config 字段")

    args = parser.parse_args(argv)
    try:
        return {"serve": _serve, "check": _check, "explain": _explain, "operators": _operators}[args.cmd](args)
    except ConfigError as e:
        print(f"config errors ({len(e.errors)}):", file=sys.stderr)
        for line in e.errors:
            print(f"  ✗ {line}", file=sys.stderr)
        return 1


def _serve(args: argparse.Namespace) -> int:
    from .web import create_app  # 延迟导入：check / operators 不需要 Flask

    app = create_app(args.conf)
    srv = app.extensions["lowcode"].server
    app.run(host=args.host or srv.host, port=args.port or srv.port, threaded=True)
    return 0


def _check(args: argparse.Namespace) -> int:
    rt = build_runtime(args.conf)
    try:
        s = rt.server
        print(f"config ok: {s.root} ({len(s.groups)} groups, {len(rt.plans)} apis, "
              f"{len(rt.datasources.items())} datasources)")
        for p in rt.plans:
            shape = f"{len(p.nodes)} 节点 / {len(p.levels)} 层"
            print(f"  {p.method:<6} {p.url:<28} [{p.group.key}] {shape:<12} {p.api.name}")
    finally:
        rt.close()
    return 0


def _explain(args: argparse.Namespace) -> int:
    rt = build_runtime(args.conf)
    try:
        plans = [p for p in rt.plans if not args.api or args.api in p.url]
        if args.api and not plans:
            print(f"no api matches {args.api!r}", file=sys.stderr)
            return 1
        for p in plans:
            print(f"{p.method:<6} {p.url}  {p.api.name}")
            if p.api.desc:
                print(f"  desc: {p.api.desc}")
            ins = ", ".join(f"{d.name}({d.type}{', required' if d.required else ''})" for d in p.inputs.defs)
            print(f"  inputs: {ins or '-'}")
            outs = ", ".join(f"{o.name}({o.type})" for o in p.api.outputs)
            print(f"  outputs: {outs or '-'}")
            for i, level in enumerate(p.levels, 1):
                print(f"  level {i}{' (parallel)' if len(level) > 1 else ''}:")
                for nid in level:
                    n = p.nodes[nid]
                    result = "  <- result" if nid == p.result else ""
                    print(f"    {nid:<14} {n.op.name:<14} {n.effective_desc}{result}")
            shape = response_shape(p)
            if shape is not None:
                print(f"  response: {json.dumps(shape, ensure_ascii=False)}")
            print()
    finally:
        rt.close()
    return 0


def _operators(args: argparse.Namespace) -> int:
    for op in list_operators():
        print(f"\n{op.name}  [{op.category}]  {op.desc}")
        for key, f in op.spec.items():
            flags = "必填" if f.required else f"默认 {f.default!r}"
            dyn = "  {{ }}" if f.dynamic else ""
            print(f"    {key:<14} {f.type_name:<10} {flags:<16}{dyn}  {f.desc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
