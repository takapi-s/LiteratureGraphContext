from pathlib import Path

from litgraph.utils import db_lock


def test_litgraph_subcommand_detects_serve_mcp():
    cmdline = "bash -lc cd /tmp/project && exec /usr/bin/litgraph serve-mcp"
    assert db_lock._litgraph_subcommand(cmdline) == "serve-mcp"


def test_litgraph_subcommand_detects_watch():
    cmdline = "/usr/bin/python3 /home/user/.local/bin/litgraph watch"
    assert db_lock._litgraph_subcommand(cmdline) == "watch"


def test_litgraph_subcommand_ignores_build():
    cmdline = "/usr/bin/python3 /home/user/.local/bin/litgraph build"
    assert db_lock._litgraph_subcommand(cmdline) is None


def test_same_project_matches_project_in_cmdline():
    project = Path("/tmp/project")
    db_path = project / ".litgraph/db/literature.kuzu"
    cmdline = "bash -lc cd /tmp/project && exec litgraph serve-mcp"
    assert db_lock._same_project(project, db_path, cmdline, None) is True


def test_same_project_matches_cwd():
    project = Path("/tmp/project")
    db_path = project / ".litgraph/db/literature.kuzu"
    assert db_lock._same_project(project, db_path, "litgraph watch", project) is True


def test_same_project_matches_litgraph_project_root_env():
    project = Path("/tmp/toyopay")
    db_path = project / ".litgraph/db/literature.kuzu"
    assert (
        db_lock._same_project(
            project,
            db_path,
            "litgraph serve-mcp",
            Path("/home/pocky"),
            env_project_root=project,
        )
        is True
    )


def test_release_db_lock_stops_matching_processes(monkeypatch):
    db_path = Path("/tmp/project/.litgraph/db/literature.kuzu")
    target = db_lock.LitgraphProcess(pid=1234, command="watch", cmdline="litgraph watch")
    killed: list[int] = []

    monkeypatch.setattr(db_lock, "find_conflicting_processes", lambda *_args, **_kwargs: [target])
    monkeypatch.setattr(db_lock.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        db_lock.os,
        "kill",
        lambda pid, _sig: killed.append(pid),
    )

    stopped = db_lock.release_db_lock(db_path)
    assert stopped == [target]
    assert killed == [1234]
