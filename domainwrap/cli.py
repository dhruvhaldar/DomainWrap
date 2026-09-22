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
    args = parser.parse_args()
    try:
        result = generate_domain(args.input, tuple(args.margins), args.subtract)
        path = save_domain(result.mesh, args.output)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(2, f"domainwrap: {exc}\n")
    print(json.dumps({"output": str(path), "source_bounds": result.source_bounds,
                      "domain_bounds": result.domain_bounds, "warnings": result.warnings}))


if __name__ == "__main__":
    main()
