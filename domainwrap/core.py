"""Geometry operations shared by the CLI and browser interface."""

import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

SUPPORTED = {".stl", ".vtp"}


@dataclass
class DomainResult:
    mesh: pv.PolyData
    source_bounds: tuple[float, ...]
    domain_bounds: tuple[float, ...]
    warnings: list[str]


def load_surface(path: str | Path) -> pv.PolyData:
    source = Path(path)
    if source.suffix.lower() not in SUPPORTED:
        raise ValueError("Input must be an STL or VTP file")
    if not source.is_file():
        raise FileNotFoundError(source)
    mesh = pv.read(source)
    if not isinstance(mesh, pv.PolyData) or mesh.n_points == 0:
        raise ValueError("Input must contain nonempty polygonal surface geometry")
    if not np.isfinite(mesh.points).all():
        raise ValueError("Input has non-finite coordinates")
    return mesh


def _triangle_surface(mesh: pv.PolyData) -> pv.PolyData:
    """Triangulate polygons; reject lines/vertices for solid subtraction."""
    if mesh.n_faces == 0 or mesh.n_lines or mesh.n_verts or mesh.n_strips:
        raise ValueError("Subtraction requires a polygon-only closed surface")
    return mesh.triangulate().clean()


def _watertight(mesh: pv.PolyData) -> bool:
    triangles = _triangle_surface(mesh)
    faces = triangles.faces.reshape(-1, 4)[:, 1:]
    solid = trimesh.Trimesh(vertices=triangles.points, faces=faces, process=False)
    return bool(solid.is_watertight)


def get_geometry_info(source: str | Path | pv.PolyData) -> dict:
    """Return bounding box, extents, and recommended relative margins."""
    mesh = source if isinstance(source, pv.PolyData) else load_surface(source)
    b = tuple(float(v) for v in mesh.bounds)
    lx = max(0.0, b[1] - b[0])
    ly = max(0.0, b[3] - b[2])
    lz = max(0.0, b[5] - b[4])
    char_len = max(lx, ly, lz)
    ref_x = lx if lx > 0 else (char_len if char_len > 0 else 1.0)
    ref_y = ly if ly > 0 else (char_len if char_len > 0 else 1.0)
    ref_z = lz if lz > 0 else (char_len if char_len > 0 else 1.0)
    # Relative default margins: -X (1.0x), +X (3.0x wake), -Y (1.0x), +Y (1.0x), -Z (0.2x ground), +Z (1.5x top)
    default_margins = (
        round(1.0 * ref_x, 3),
        round(3.0 * ref_x, 3),
        round(1.0 * ref_y, 3),
        round(1.0 * ref_y, 3),
        round(0.2 * ref_z, 3),
        round(1.5 * ref_z, 3),
    )
    max_val = round(max(ref_x * 5, ref_y * 5, ref_z * 5, 10.0), 2)
    step = round(char_len / 100.0, 3) if char_len > 0 else 0.1
    step = max(step, 0.001)
    return {
        "bounds": b,
        "extents": (lx, ly, lz),
        "default_margins": default_margins,
        "slider_max": max_val,
        "slider_step": step,
    }


def generate_domain(
    input_path: str | Path,
    margins: tuple[float, float, float, float, float, float],
    subtract: bool = False,
    source_scale: float = 1.0,
    domain_scale: float = 1.0,
) -> DomainResult:
    """Margins are ordered -X, +X, -Y, +Y, -Z, +Z."""
    if source_scale <= 0 or not np.isfinite(source_scale):
        raise ValueError("Source scale must be a positive finite number")
    if domain_scale <= 0 or not np.isfinite(domain_scale):
        raise ValueError("Domain scale must be a positive finite number")
    if len(margins) != 6 or not np.isfinite(margins).all() or any(v < 0 for v in margins):
        raise ValueError("Exactly six finite, nonnegative margins are required")
    source = load_surface(input_path)
    if source_scale != 1.0:
        source = source.copy()
        source.points = source.points * source_scale
    if domain_scale != 1.0:
        scaled_margins = (
            float(margins[0] * domain_scale),
            float(margins[1] * domain_scale),
            float(margins[2] * domain_scale),
            float(margins[3] * domain_scale),
            float(margins[4] * domain_scale),
            float(margins[5] * domain_scale),
        )
    else:
        scaled_margins = margins
    b = tuple(float(v) for v in source.bounds)
    bounds = (
        b[0] - scaled_margins[0], b[1] + scaled_margins[1],
        b[2] - scaled_margins[2], b[3] + scaled_margins[3],
        b[4] - scaled_margins[4], b[5] + scaled_margins[5],
    )
    if any(bounds[i] >= bounds[i + 1] for i in (0, 2, 4)):
        raise ValueError("Domain must have positive extent on every axis")
    notes: list[str] = []
    try:
        if not _watertight(source):
            notes.append("Input is not watertight; subtraction may fail or be invalid")
    except ValueError as exc:
        notes.append(f"Watertight check unavailable: {exc}")
    box = pv.Box(bounds=bounds).triangulate().clean()
    if subtract:
        if any(v <= 0 for v in margins):
            raise ValueError("Subtraction needs positive clearance on all six sides")
        if notes:
            warnings.warn(notes[0], stacklevel=2)
        surface = _triangle_surface(source)
        # A strictly enclosed obstacle has no intersection curve with the box.
        # VTK's boolean_difference cannot handle that case reliably. The fluid
        # boundary is the union of the outer shell and reversed inner shell.
        try:
            cavity = box.append_polydata(surface.copy().flip_faces()).clean()
        except Exception as exc:
            raise RuntimeError(f"Fluid boundary construction failed: {exc}") from exc
        if cavity.n_faces == 0 or not _watertight(cavity):
            raise RuntimeError("Boolean subtraction did not produce a watertight surface")
        box = cavity
    return DomainResult(box, b, bounds, notes)


def save_domain(mesh: pv.PolyData, output_path: str | Path) -> Path:
    output = Path(output_path)
    if output.suffix.lower() not in SUPPORTED:
        raise ValueError("Output must end in .stl or .vtp")
    output.parent.mkdir(parents=True, exist_ok=True)
    mesh.save(output, binary=output.suffix.lower() == ".stl")
    return output
