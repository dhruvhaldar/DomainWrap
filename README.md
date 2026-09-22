# DomainWrap

Generate an outer computational boundary from STL or VTP geometry, optionally subtracting a closed obstacle to form a fluid cavity. Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
uv run python -m domainwrap.app --port 7860
```

Open `http://127.0.0.1:7860` in a browser. The Python-defined UI places six face-offset sliders beside a rotatable 3D preview. Releasing a slider regenerates the domain and downloadable file. The sliders cover 0–10,000 source units; use the CLI for larger offsets.

For headless use:

```powershell
uv run python -m domainwrap.cli --input driver_model.vtp --output fluid_domain.vtp --margins 500 2000 500 500 50 800 --subtract
```

Margin order is **−X, +X, −Y, +Y, −Z, +Z**, in the same units as the source coordinates. Without `--subtract`, the output is only the watertight outer box; with it, the output contains an outer shell and an inward-facing obstacle shell. The obstacle must be a closed, triangulable polygonal surface fully separated from the box. Boolean failure produces an error, never a silently substituted box. Mixed lines/vertices in VTP are supported for bounding-box generation but not subtraction. Preview uses temporary STL because Gradio's Model3D does not accept VTP directly; exported VTP remains VTP.

This is a surface boundary generator, not a volumetric mesher. No coordinate-system or unit conversion is performed. Input scalar/attribute arrays are not preserved in the generated domain, and STL cannot store them.
