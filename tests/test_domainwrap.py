import subprocess
import sys

import gradio as gr
import pytest
import pyvista as pv

from domainwrap.app import build, create_app
from domainwrap.core import generate_domain, save_domain


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "obstacle.vtp"
    pv.Cube().triangulate().save(path)
    return path


def test_box_and_formats(source, tmp_path):
    result = generate_domain(source, (1, 2, 3, 4, 5, 6))
    assert result.domain_bounds == pytest.approx((-1.5, 2.5, -3.5, 4.5, -5.5, 6.5))
    assert result.mesh.n_faces == 12
    for extension in ("stl", "vtp"):
        path = save_domain(result.mesh, tmp_path / f"domain.{extension}")
        assert pv.read(path).n_faces == 12


def test_subtraction(source):
    result = generate_domain(source, (1, 1, 1, 1, 1, 1), subtract=True)
    assert result.mesh.n_faces > 12
    assert result.warnings == []


def test_invalid_margin(source):
    with pytest.raises(ValueError, match="nonnegative"):
        generate_domain(source, (-1, 1, 1, 1, 1, 1))


def test_cli(source, tmp_path):
    output = tmp_path / "cli.stl"
    result = subprocess.run(
        [sys.executable, "-m", "domainwrap.cli", "--input", str(source),
         "--output", str(output), "--margins", "1", "1", "1", "1", "1", "1"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.is_file()


def test_web_app_builds():
    assert isinstance(create_app(), gr.Blocks)


def test_web_generation(source, monkeypatch, tmp_path):
    monkeypatch.setattr("domainwrap.app.tempfile.mkdtemp", lambda **_: str(tmp_path))
    preview, output, report = build(str(source), 1, 1, 1, 1, 1, 1, False, "vtp")
    assert pv.read(preview).n_faces == 12
    assert pv.read(output).n_faces == 12
    assert "Domain bounds" in report
