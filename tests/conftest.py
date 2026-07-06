import pytest


@pytest.fixture
def project_tmp(tmp_path):
    from litgraph.cli.config_manager import init_project
    init_project(tmp_path)
    (tmp_path / "papers").mkdir()
    return tmp_path
