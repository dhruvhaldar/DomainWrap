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


def generate_domain(
    input_path: str | Path,
    margins: tuple[float, float, float, float, float, float],
    subtract: bool = False,
) -> DomainResult:
    """Margins are ordered -X, +X, -Y, +Y, -Z, +Z."""
    if len(margins) != 6 or not np.isfinite(margins).all() or any(v < 0 for v in margins):
        raise ValueError("Exactly six finite, nonnegative margins are required")
    source = load_surface(input_path)
    b = tuple(float(v) for v in source.bounds)
    bounds = (
        b[0] - margins[0], b[1] + margins[1],
        b[2] - margins[2], b[3] + margins[3],
        b[4] - margins[4], b[5] + margins[5],
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
