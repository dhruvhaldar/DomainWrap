# DomainWrap

**DomainWrap** is a fast, lightweight computational domain generator for Computational Fluid Dynamics (CFD) and aerodynamic simulations. It builds bounding outer flow domains around complex 3D surface geometries (STL and VTP formats), optionally subtracting closed obstacle surfaces to produce watertight fluid cavities.

DomainWrap features both a **headless command-line interface (CLI)** for automated scripting/pipelines and a **modern interactive Web UI** with a seamless WebGL 3D visualizer that requires zero external web framework dependencies.

---

## Key Features

- **Relative Boundary Sizing:** Uploaded surface geometries automatically initialize with CFD-recommended proportional domain margins relative to the object's physical dimensions ($-X$ inlet, $+X$ wake, lateral sides, ground clearance, and ceiling).
- **Flexible Multi-Mode Scaling:** Scale source geometry coordinates, domain boundary margins, or both together (e.g. converting between millimeters and meters with a single click or CLI flag).
- **Seamless 3D Web Visualizer:** Built on Three.js with WebGL. Moving sliders or changing scale parameters updates the 3D domain box **instantly client-side** without flickering, page reloading, or resetting camera orbit and zoom.
- **Watertight Fluid Cavity Extraction:** Robust surface subtraction for CFD external flow domains. Preserves closed outer boundaries and inverted inner obstacle shells.
- **Ultra-Lean Dependencies:** Pure Python backend using standard library `http.server.ThreadingHTTPServer` (zero Gradio or heavy web framework bloat). Depends only on PyVista, Trimesh, and NumPy.
- **Dual Format Support:** Full support for both binary/ASCII STL (`.stl`) and VTK XML PolyData (`.vtp`) formats.

---

## Requirements and Installation

DomainWrap requires **Python 3.10+** and uses [uv](https://docs.astral.sh/uv/) for fast, deterministic dependency management.

```powershell
# Clone the repository
git clone https://github.com/dhruvhaldar/DomainWrap.git
cd DomainWrap

# Sync dependencies into virtual environment
uv sync
```

---

## Interactive Web Application

Start the local web application:

```powershell
uv run python -m domainwrap.app --port 7860
```

Open `http://127.0.0.1:7860` in your web browser.

### Web Interface Workflow

1. **Upload Surface:** Drag and drop or browse for an `.stl` or `.vtp` geometry file.
2. **CFD Presets & Multipliers:**
   - Quick domain presets: **Standard** (3× wake), **Automotive** (5× wake, low ground clearance), **Aerospace** (6× wake, free-stream all sides), **Long Wake** (8× wake).
   - **Wake Multiplier Control:** Directly set the wake length using the multiplier input or quick chips (**3×**, **5×**, **8×**, **10×**) &mdash; the $+X$ offset updates instantly.
   - **Inlet & Side Multipliers:** Dedicated multiplier inputs for $-X$, $\pm Y$ with a **Symmetric ±Y** toggle.
   - **Ground & Ceiling Multipliers:** Set $-Z$ ground clearance (e.g. `0×` for ground contact or `0.2×`) and $+Z$ top clearance.
3. **CFD Diagnostics:**
   - Live **Domain Size** ($L_x \times L_y \times L_z$).
   - Live **Frontal Blockage Ratio** ($\%$ frontal obstacle area / domain cross-section) with color-coded status badges ($<3\%$ recommended for minimal wall interference).
4. **Scaling:**
   - Choose target: **Both** (geometry + domain), **Source** only, or **Domain** only.
   - Set a custom factor or use quick presets (`mm → m: 0.001`, `m → mm: 1000`, `1.0`).
5. **Interactive 3D Viewport:**
   - Drag boundary sliders or multiplier chips to see the semi-transparent bounding box update seamlessly in real time.
   - Orbit, pan, and zoom around the model without visualizer reloads or camera jumping.
   - Toggle **Edges Only** wireframe mode or click **Reset View** as needed.
6. **Generate & Download:**
   - Toggle **Subtract model (fluid cavity)** if you require an inner fluid cavity.
   - Select output format (**VTP** or **STL**). When **STL** is selected, choose between **Binary** (compact, recommended for CFD meshing) and **ASCII** (human-readable text).
   - Click **Generate Domain**, inspect the calculated bounding coordinates and warnings, and click **Download Domain**.

---

## Headless CLI Usage

DomainWrap can be run in automated scripts, CI/CD pipelines, and HPC batch jobs without launching a browser.

### Syntax

```powershell
uv run python -m domainwrap.cli --input <INPUT_FILE> --output <OUTPUT_FILE> --margins <MX> <PX> <MY> <PY> <MZ> <PZ> [OPTIONS]
```

### CLI Arguments

| Argument | Type | Description |
| :--- | :--- | :--- |
| `--input` | Path (required) | Path to input `.stl` or `.vtp` geometry. |
| `--output` | Path (required) | Path for generated `.stl` or `.vtp` domain surface. |
| `--margins` | 6 Floats (required) | Face offsets in order: `-X +X -Y +Y -Z +Z`. |
| `--subtract` | Flag (optional) | Subtract closed obstacle from outer box to create fluid cavity. |
| `--scale` | Float (default: `1.0`) | Uniform scale factor applied to both source geometry and domain. |
| `--source-scale` | Float (optional) | Scale factor applied strictly to source geometry coordinates. |
| `--domain-scale` | Float (optional) | Scale factor applied strictly to domain boundary margins. |
| `--ascii` | Flag (optional) | Save STL in ASCII format (default: binary). |

### CLI Examples

**1. Generate an external flow domain around a vehicle (in millimeters):**
```powershell
uv run python -m domainwrap.cli `
  --input car.stl `
  --output domain.vtp `
  --margins 2000 6000 1500 1500 50 2500 `
  --subtract
```

**2. Convert millimeter model to meters and scale domain simultaneously:**
```powershell
uv run python -m domainwrap.cli `
  --input wing_mm.stl `
  --output wing_m_domain.stl `
  --margins 1000 3000 500 500 500 1000 `
  --scale 0.001 `
  --subtract
```

**3. Output JSON Response:**
On completion, the CLI prints machine-readable JSON to standard output:
```json
{
  "output": "C:\\path\\to\\domain.vtp",
  "source_bounds": [-0.5, 0.5, -0.5, 0.5, -0.5, 0.5],
  "domain_bounds": [-2.5, 4.5, -1.5, 1.5, -0.7, 2.0],
  "warnings": []
}
```

---

## Python API Usage

You can also import and use DomainWrap directly within Python scripts:

```python
from domainwrap.core import generate_domain, get_geometry_info, save_domain

# 1. Inspect geometry extents and get CFD-recommended relative margins
info = get_geometry_info("obstacle.stl")
print("Extents (Lx, Ly, Lz):", info["extents"])
print("Recommended default margins:", info["default_margins"])

# 2. Generate computational domain
# Margins: (-X, +X, -Y, +Y, -Z, +Z)
result = generate_domain(
    input_path="obstacle.stl",
    margins=info["default_margins"],
    subtract=True,
    source_scale=1.0,
    domain_scale=1.0,
)

# 3. Save domain mesh (supports VTP and binary/ASCII STL)
output_path = save_domain(result.mesh, "fluid_domain.stl", binary=True)  # set binary=False for ASCII STL
print(f"Saved domain to {output_path}")
print(f"Domain Bounds: {result.domain_bounds}")
```

---

## Technical Notes & Geometry Rules

1. **Margin Ordering:** Margin order is always strictly **−X, +X, −Y, +Y, −Z, +Z**, expressed in the same spatial units as the geometry coordinates.
2. **Watertight Subtraction:**
   - Without `--subtract`, DomainWrap generates a watertight 6-sided bounding box.
   - With `--subtract`, the output contains an outer boundary box and an inward-facing obstacle shell. The input obstacle must be a closed, watertight 2-manifold surface.
   - If boolean subtraction fails or produces a non-watertight cavity, an explicit error is raised; DomainWrap never silently substitutes an invalid outer box.
3. **Surface Generator vs Volumetric Mesher:** DomainWrap produces surface boundaries (`PolyData`), not volumetric 3D meshes (e.g. tetrahedral or polyhedral meshes).
4. **Attribute Arrays:** Input scalar/vector field attributes on input surfaces are not preserved in the domain box boundary.

---

## Development and Testing

Install development dependencies:

```powershell
uv sync --extra dev
```

Run test suite:

```powershell
uv run pytest
```

Run lint checks:

```powershell
uv run ruff check domainwrap tests
```

Run static type checking with [ty](https://github.com/astral-sh/ty):

```powershell
uv run ty check
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
