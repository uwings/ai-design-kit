"""ADK 统一 CLI。

用法:
  python -m engine.cli <subcommand> [args]

阶段 1 子命令（确定性，全部实现）:
  validate-contracts [glob...]   校验组件契约（默认 systems/*/components/*.json）
  validate-tokens [--system S]   校验 token 图（循环/模式完整性）
  validate-graph <graph.json>    校验语义图（component/slot/variant/token/a11y）
  validate-ops <ops.json>        应用 ops 构图后校验
  compile-pencil <graph.json> -o <out.pen>      语义图 → Pencil .pen
  compile-code <graph.json> --framework react|html -o <out>

阶段 3 子命令（index/retrieve）见后续；本文件 import 安全。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from . import schemas
from .contract import Contract, ContractIndex
from .kit import Kit, PROJECT_ROOT
from .tokens import TokenGraph, validate_token_graph
from .graph import SemanticGraph
from .ops import apply_ops
from .validator import validate_graph, validate_ops
from .compilers import pencil as pencil_compiler
from .compilers import react as react_compiler
from .compilers import html as html_compiler


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str, data) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: str, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.rstrip() + "\n", encoding="utf-8")


def _system_for(graph: Optional[dict], args) -> str:
    if graph and graph.get("project", {}).get("system"):
        return graph["project"]["system"]
    return getattr(args, "system", None) or Kit.load().default_system


# ---- subcommands ----

def cmd_validate_contracts(args) -> int:
    patterns = args.files or ["systems/*/components/*.contract.json"]
    files: List[Path] = []
    for pat in patterns:
        files.extend(sorted(PROJECT_ROOT.glob(pat)))
    if not files:
        print("[validate-contracts] no files matched.")
        return 1
    total = ok = 0
    failures = []
    for f in files:
        total += 1
        try:
            Contract.from_file(f)
            ok += 1
            print(f"  OK   {f.relative_to(PROJECT_ROOT)}")
        except schemas.ContractError as e:
            failures.append((f, e))
            print(f"  FAIL {f.relative_to(PROJECT_ROOT)}")
            for line in str(e).splitlines()[1:4]:
                print("       " + line)
    print(f"\n{ok}/{total} contracts valid.")
    return 0 if ok == total else 2


def cmd_validate_tokens(args) -> int:
    kit = Kit.load()
    system = args.system or kit.default_system
    tg = kit.load_tokens(system)
    if tg is None:
        print(f"[validate-tokens] no token-graph.json for system '{system}'")
        return 1
    issues = validate_token_graph(tg)
    if not issues:
        print(f"[validate-tokens] {system}: OK ({len(tg.tokens)} tokens, modes={tg.modes})")
        return 0
    for i in issues:
        print(f"  [{i.kind}] {i.message}")
    print(f"\n{len(issues)} token issue(s).")
    return 2


def cmd_validate_graph(args) -> int:
    data = _load_json(args.file)
    graph = SemanticGraph.from_dict(data)
    kit = Kit.load()
    system = _system_for(data, args)
    idx = kit.load_contracts(system)
    tg = kit.load_tokens(system)
    report = validate_graph(graph, idx, tg)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.passed else 2


def cmd_validate_ops(args) -> int:
    ops = _load_json(args.file)
    schemas.validate_or_raise(ops, "semantic-ops")
    kit = Kit.load()
    system = args.system or kit.default_system
    idx = kit.load_contracts(system)
    tg = kit.load_tokens(system)
    report = validate_ops(ops, idx, tg, system=system)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.passed else 2


def cmd_compile_pencil(args) -> int:
    graph = SemanticGraph.from_dict(_load_json(args.file))
    kit = Kit.load()
    system = _system_for(_load_json(args.file), args)
    idx = kit.load_contracts(system)
    tg = kit.load_tokens(system)
    pen = pencil_compiler.compile_page(graph, idx, tg)
    _write_json(args.output or "pencil/generated/page.pen", pen)
    print(f"[compile-pencil] {system}: {len(pen.get('variables', {}))} vars, "
          f"{sum(len(p.get('children', [])) for p in pen.get('children', []))} top frames → {args.output}")
    return 0


def cmd_compile_library(args) -> int:
    kit = Kit.load()
    system = args.system or kit.default_system
    idx = kit.load_contracts(system)
    tg = kit.load_tokens(system)
    pen = pencil_compiler.compile_library(idx, tg)
    out = args.output or f"systems/{system}/pencil/{system}.lib.pen"
    _write_json(out, pen)
    print(f"[compile-library] {system}: {len(idx.registered_ids())} reusable components → {out}")
    return 0


def cmd_compile_code(args) -> int:
    data = _load_json(args.file)
    graph = SemanticGraph.from_dict(data)
    kit = Kit.load()
    system = _system_for(data, args)
    idx = kit.load_contracts(system)
    tg = kit.load_tokens(system)
    if args.framework == "react":
        text = react_compiler.compile_react(graph, idx, tg)
        out = args.output or "generated-code/page.tsx"
    else:
        text = html_compiler.compile_html(graph, idx, tg)
        out = args.output or "generated-code/page.html"
    _write_text(out, text)
    print(f"[compile-code] {system}/{args.framework} → {out}")
    return 0


def cmd_index(args) -> int:
    from .indexer import build_index
    kit = Kit.load()
    build_index(kit, systems=args.systems or kit.systems())
    print(f"[index] built cards + intent-index for: {', '.join(args.systems or kit.systems())}")
    return 0


def cmd_retrieve(args) -> int:
    from .retriever import retrieve
    kit = Kit.load()
    pack = retrieve(intent=args.intent, system=args.system or kit.default_system, query=args.query or "")
    print(json.dumps(pack, ensure_ascii=False, indent=2))
    return 0


def cmd_apply_correction(args) -> int:
    from .feedback import apply_correction
    correction = _load_json(args.file)
    summary = apply_correction(correction, write=not args.dry_run)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def cmd_release(args) -> int:
    from .release import release
    changelog = release(kind=args.bump, system=args.system, notes=args.notes or "")
    print(json.dumps(changelog, ensure_ascii=False, indent=2))
    return 0


def cmd_export_kc(args) -> int:
    from .ingest.export_for_kc import export_for_kc
    kit = Kit.load()
    manifest = export_for_kc(args.system or kit.default_system)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def cmd_pencil_verify(args) -> int:
    from .compilers.pencil_mcp import verify_pen_structure, verify_with_mcp
    pen = _load_json(args.file)
    rep = verify_pen_structure(pen)
    out = rep.to_dict()
    out["mcp"] = verify_with_mcp(args.file)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if rep.passed else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="adk", description="AI Design Kit 确定性引擎 CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("validate-contracts", help="校验组件契约")
    sp.add_argument("files", nargs="*")
    sp.set_defaults(func=cmd_validate_contracts)

    sp = sub.add_parser("validate-tokens", help="校验 token 图")
    sp.add_argument("--system", default=None)
    sp.set_defaults(func=cmd_validate_tokens)

    sp = sub.add_parser("validate-graph", help="校验语义图")
    sp.add_argument("file")
    sp.add_argument("--system", default=None)
    sp.set_defaults(func=cmd_validate_graph)

    sp = sub.add_parser("validate-ops", help="应用 ops 后校验")
    sp.add_argument("file")
    sp.add_argument("--system", default=None)
    sp.set_defaults(func=cmd_validate_ops)

    sp = sub.add_parser("compile-pencil", help="语义图 → Pencil .pen")
    sp.add_argument("file")
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument("--system", default=None)
    sp.set_defaults(func=cmd_compile_pencil)

    sp = sub.add_parser("compile-library", help="契约 → Pencil 库")
    sp.add_argument("--system", default=None)
    sp.add_argument("-o", "--output", default=None)
    sp.set_defaults(func=cmd_compile_library)

    sp = sub.add_parser("compile-code", help="语义图 → React/HTML")
    sp.add_argument("file")
    sp.add_argument("--framework", choices=["react", "html"], default="react")
    sp.add_argument("-o", "--output", default=None)
    sp.add_argument("--system", default=None)
    sp.set_defaults(func=cmd_compile_code)

    sp = sub.add_parser("index", help="生成 cards + 意图路由表")
    sp.add_argument("--systems", nargs="*", default=None)
    sp.set_defaults(func=cmd_index)

    sp = sub.add_parser("retrieve", help="意图路由组装最小知识包")
    sp.add_argument("--intent", required=True)
    sp.add_argument("--query", default="")
    sp.add_argument("--system", default=None)
    sp.set_defaults(func=cmd_retrieve)

    sp = sub.add_parser("apply-correction", help="应用一条纠错（落盘 + patch）")
    sp.add_argument("file")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_apply_correction)

    sp = sub.add_parser("release", help="版本 bump + changelog + KC 导出")
    sp.add_argument("--bump", choices=["patch", "minor", "major"], default="patch")
    sp.add_argument("--system", default=None)
    sp.add_argument("--notes", default="")
    sp.set_defaults(func=cmd_release)

    sp = sub.add_parser("export-kc", help="导出 KC 消费清单（预留接入点）")
    sp.add_argument("--system", default=None)
    sp.set_defaults(func=cmd_export_kc)

    sp = sub.add_parser("pencil-verify", help=".pen 结构自检 + 实时 MCP 协议")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_pencil_verify)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except schemas.ContractError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa
        print(f"[adk] error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
