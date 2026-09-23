import json
import subprocess
import sys
import threading
import urllib.request
from http import HTTPStatus

import pytest
import pyvista as pv

from domainwrap.app import DomainWrapServer, build, create_app
from domainwrap.core import generate_domain, get_geometry_info, save_domain


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


def test_stl_ascii_and_binary(source, tmp_path):
    result = generate_domain(source, (1, 1, 1, 1, 1, 1))
    bin_path = save_domain(result.mesh, tmp_path / "domain_bin.stl", binary=True)
    asc_path = save_domain(result.mesh, tmp_path / "domain_asc.stl", binary=False)

    assert bin_path.read_bytes()[:5] != b"solid"
    assert asc_path.read_bytes().startswith(b"solid")
    assert pv.read(bin_path).n_faces == 12
    assert pv.read(asc_path).n_faces == 12


def test_subtraction(source):
    result = generate_domain(source, (1, 1, 1, 1, 1, 1), subtract=True)
    assert result.mesh.n_faces > 12
    assert result.warnings == []


def test_invalid_margin(source):
    with pytest.raises(ValueError, match="nonnegative"):
        generate_domain(source, (-1, 1, 1, 1, 1, 1))


def test_geometry_info(source):
    info = get_geometry_info(source)
    assert info["bounds"] == pytest.approx((-0.5, 0.5, -0.5, 0.5, -0.5, 0.5))
    assert info["extents"] == pytest.approx((1.0, 1.0, 1.0))
    # Default CFD margins: 1.0x, 3.0x, 1.0x, 1.0x, 0.2x, 1.5x
    assert info["default_margins"] == (1.0, 3.0, 1.0, 1.0, 0.2, 1.5)


def test_scaling_source(source):
    # Scale source by 2.0 (Cube from [-0.5, 0.5] becomes [-1.0, 1.0])
    result = generate_domain(source, (1, 1, 1, 1, 1, 1), source_scale=2.0, domain_scale=1.0)
    assert result.source_bounds == pytest.approx((-1.0, 1.0, -1.0, 1.0, -1.0, 1.0))
    assert result.domain_bounds == pytest.approx((-2.0, 2.0, -2.0, 2.0, -2.0, 2.0))


def test_scaling_domain(source):
    # Source untouched ([-0.5, 0.5]), margins scaled by 2.0 (1 -> 2)
    result = generate_domain(source, (1, 1, 1, 1, 1, 1), source_scale=1.0, domain_scale=2.0)
    assert result.source_bounds == pytest.approx((-0.5, 0.5, -0.5, 0.5, -0.5, 0.5))
    assert result.domain_bounds == pytest.approx((-2.5, 2.5, -2.5, 2.5, -2.5, 2.5))


def test_scaling_both(source):
    # Both scaled by 0.5: source is [-0.25, 0.25], margins are 0.5
    result = generate_domain(source, (1, 1, 1, 1, 1, 1), source_scale=0.5, domain_scale=0.5)
    assert result.source_bounds == pytest.approx((-0.25, 0.25, -0.25, 0.25, -0.25, 0.25))
    assert result.domain_bounds == pytest.approx((-0.75, 0.75, -0.75, 0.75, -0.75, 0.75))


def test_cli(source, tmp_path):
    output = tmp_path / "cli.stl"
    result = subprocess.run(
        [sys.executable, "-m", "domainwrap.cli", "--input", str(source),
         "--output", str(output), "--margins", "1", "1", "1", "1", "1", "1"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.is_file()


def test_cli_scaling(source, tmp_path):
    output = tmp_path / "cli_scaled.stl"
    result = subprocess.run(
        [sys.executable, "-m", "domainwrap.cli", "--input", str(source),
         "--output", str(output), "--margins", "1", "1", "1", "1", "1", "1",
         "--scale", "2.0"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.is_file()
    data = json.loads(result.stdout)
    assert data["source_bounds"] == pytest.approx((-1.0, 1.0, -1.0, 1.0, -1.0, 1.0))
    assert data["domain_bounds"] == pytest.approx((-3.0, 3.0, -3.0, 3.0, -3.0, 3.0))


def test_cli_ascii(source, tmp_path):
    output = tmp_path / "cli_ascii.stl"
    result = subprocess.run(
        [sys.executable, "-m", "domainwrap.cli", "--input", str(source),
         "--output", str(output), "--margins", "1", "1", "1", "1", "1", "1",
         "--ascii"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.is_file()
    assert output.read_bytes().startswith(b"solid")


def test_web_app_builds():
    app = create_app(port=0)
    assert isinstance(app, DomainWrapServer)
    app.server_close()


def test_web_generation(source, monkeypatch, tmp_path):
    monkeypatch.setattr("domainwrap.app.tempfile.mkdtemp", lambda **_: str(tmp_path))
    preview, output, report = build(str(source), 1, 1, 1, 1, 1, 1, False, "vtp")
    assert pv.read(preview).n_faces == 12
    assert pv.read(output).n_faces == 12
    assert "Domain bounds" in report


def test_server_api_flow(source):
    server = create_app(host="127.0.0.1", port=0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    try:
        # 1. GET /
        with urllib.request.urlopen(f"{base_url}/") as resp:
            assert resp.status == HTTPStatus.OK
            html = resp.read().decode("utf-8")
            assert "DomainWrap" in html
            assert 'rel="icon"' in html

        with urllib.request.urlopen(f"{base_url}/favicon.ico") as resp:
            assert resp.status == HTTPStatus.OK
            assert "image/svg+xml" in resp.headers.get("Content-Type", "")
            assert b"<svg" in resp.read()

        # 2. POST /api/upload
        source_bytes = source.read_bytes()
        req = urllib.request.Request(
            f"{base_url}/api/upload",
            data=source_bytes,
            headers={"X-Filename": "obstacle.vtp"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == HTTPStatus.OK
            upload_data = json.loads(resp.read().decode("utf-8"))
            assert "file_id" in upload_data
            assert upload_data["extents"] == [1.0, 1.0, 1.0]
            assert upload_data["default_margins"] == [1.0, 3.0, 1.0, 1.0, 0.2, 1.5]

        file_id = upload_data["file_id"]

        # 3. POST /api/generate
        gen_payload = json.dumps({
            "file_id": file_id,
            "margins": [1, 2, 3, 4, 5, 6],
            "subtract": False,
            "format": "stl",
            "binary": False,
            "source_scale": 1.0,
            "domain_scale": 1.0,
        }).encode("utf-8")
        req_gen = urllib.request.Request(
            f"{base_url}/api/generate",
            data=gen_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_gen) as resp:
            assert resp.status == HTTPStatus.OK
            gen_data = json.loads(resp.read().decode("utf-8"))
            assert "download_url" in gen_data
            assert "domain_bounds" in gen_data

        # 4. GET download_url (verifying ASCII STL format)
        with urllib.request.urlopen(f"{base_url}{gen_data['download_url']}") as resp:
            assert resp.status == HTTPStatus.OK
            downloaded = resp.read()
            assert downloaded.startswith(b"solid")
    finally:
        server.shutdown()
        server.server_close()
