"""Kuzu read-only connection mode for concurrent query access."""

import subprocess
import sys
import time

from litgraph.cli.config_manager import resolve_context
from litgraph.graph.db_factory import get_graph_store
from litgraph.query.paper_finder import PaperFinder
from tests.fixtures.extracted_fixtures import build_fixture_graph


def test_read_only_store_lists_papers(project_tmp):
    ctx = resolve_context(project_tmp)
    build_fixture_graph(ctx)

    ro_store = get_graph_store(ctx.db_path, read_only=True)
    try:
        papers = ro_store.list_papers()
        assert len(papers) >= 1
        ro_store.initialize_schema()
    finally:
        ro_store.close()


def test_multiple_read_only_processes_can_coexist(project_tmp):
    ctx = resolve_context(project_tmp)
    build_fixture_graph(ctx)
    db_path = str(ctx.db_path.resolve())

    script = f"""
from pathlib import Path
from litgraph.graph.db_factory import get_graph_store
import time

store = get_graph_store(Path({db_path!r}), read_only=True)
count = len(store.list_papers())
print(count)
time.sleep(2)
store.close()
"""
    proc_a = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(0.3)
    proc_b = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    out_a, _ = proc_a.communicate(timeout=10)
    out_b, _ = proc_b.communicate(timeout=10)
    assert proc_a.returncode == 0, out_a
    assert proc_b.returncode == 0, out_b
    assert int(out_a.strip().splitlines()[0]) >= 1
    assert int(out_b.strip().splitlines()[0]) >= 1


def test_paper_finder_read_only_skips_schema_init(project_tmp):
    ctx = resolve_context(project_tmp)
    build_fixture_graph(ctx)

    finder = PaperFinder(ctx.db_path, read_only=True)
    try:
        papers = finder.list_papers()
        assert len(papers) >= 1
    finally:
        finder.close()
