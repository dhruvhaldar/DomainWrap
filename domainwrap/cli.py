"""Headless command-line entry point."""

import argparse
import json

from .core import generate_domain, save_domain


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an STL/VTP computational domain")
    parser.add_argument("--input", required=True, help="Input .stl or .vtp surface")
    parser.add_argument("--output", required=True, help="Output .stl or .vtp surface")
    parser.add_argument(
        "--margins", required=True, nargs=6, type=float,
        metavar=("MINUS_X", "PLUS_X", "MINUS_Y", "PLUS_Y", "MINUS_Z", "PLUS_Z"),
    )
    parser.add_argument("--subtract", action="store_true", help="Subtract obstacle from outer box")
    parser.add_argument("--scale", type=float, default=1.0, help="Uniform scale for both source geometry and domain")
    parser.add_argument("--source-scale", type=float, default=None, help="Scale for source geometry only")
    parser.add_argument("--domain-scale", type=float, default=None, help="Scale for domain margins only")
    parser.add_argument("--ascii", action="store_true", help="Save STL in ASCII format (default: binary)")
    args = parser.parse_args()
    source_scale = args.source_scale if args.source_scale is not None else args.scale
    domain_scale = args.domain_scale if args.domain_scale is not None else args.scale
    try:
        result = generate_domain(
            args.input,
            tuple(args.margins),
            args.subtract,
            source_scale=source_scale,
            domain_scale=domain_scale,
        )
        path = save_domain(result.mesh, args.output, binary=not args.ascii)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(2, f"domainwrap: {exc}\n")
    print(json.dumps({"output": str(path), "source_bounds": result.source_bounds,
                      "domain_bounds": result.domain_bounds, "warnings": result.warnings}))


if __name__ == "__main__":
    main()
