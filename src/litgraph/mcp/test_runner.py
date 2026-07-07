"""Run MCP tool smoke tests against a project."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from litgraph.mcp.tool_service import MCPToolService
from tests.fixtures.mcp_tool_cases import mcp_tool_cases

console = Console()


def run_mcp_smoke_tests(cwd: Optional[Path] = None, *, verbose: bool = False) -> Dict[str, Any]:
    service = MCPToolService(cwd)
    results: List[Dict[str, Any]] = []
    passed = 0
    failed = 0

    table = Table(title="MCP Tool Smoke Tests")
    table.add_column("Tool")
    table.add_column("Status")
    table.add_column("Detail")

    for case in mcp_tool_cases():
        name = case["tool"]
        args = case.get("args", {})
        try:
            payload = service.handle_tool_call(name, args)
            if case.get("allow_error"):
                ok = True
                detail = payload.get("error", "ok")
            elif case.get("no_error") and "error" in payload:
                ok = False
                detail = payload["error"]
            else:
                ok = True
                detail = "ok"
                for key in case.get("expect_keys", []):
                    if key not in payload:
                        ok = False
                        detail = f"missing {key}"
                        break
                min_list = case.get("min_list")
                if ok and min_list:
                    field, minimum = min_list
                    if len(payload.get(field, [])) < minimum:
                        ok = False
                        detail = f"{field} count < {minimum}"
            if ok:
                passed += 1
                table.add_row(name, "[green]PASS[/green]", str(detail)[:80])
            else:
                failed += 1
                table.add_row(name, "[red]FAIL[/red]", str(detail)[:80])
            results.append({"tool": name, "ok": ok, "detail": detail, "args": args})
            if verbose and not ok:
                console.print(payload)
        except Exception as exc:
            failed += 1
            table.add_row(name, "[red]ERROR[/red]", str(exc)[:80])
            results.append({"tool": name, "ok": False, "detail": str(exc), "args": args})

    console.print(table)
    console.print(f"Passed: {passed}  Failed: {failed}  Total: {passed + failed}")
    return {"passed": passed, "failed": failed, "results": results}
