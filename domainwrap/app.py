"""Pure-Python Gradio interface."""

import argparse
import tempfile
from pathlib import Path

import gradio as gr

from .core import generate_domain, save_domain


def build(input_file, mx, px, my, py, mz, pz, subtract, output_format):
    if not input_file:
        raise gr.Error("Upload an STL or VTP file first")
    try:
        result = generate_domain(input_file, (mx, px, my, py, mz, pz), subtract)
        directory = Path(tempfile.mkdtemp(prefix="domainwrap-"))
        output = save_domain(result.mesh, directory / f"fluid_domain.{output_format}")
        # Model3D accepts STL but not VTP; preview independently of export format.
        preview = save_domain(result.mesh, directory / "preview.stl")
        report = (f"Source bounds: {result.source_bounds}\n"
                  f"Domain bounds: {result.domain_bounds}\n"
                  + "\n".join(result.warnings))
        return str(preview), str(output), report
    except (ValueError, RuntimeError, OSError) as exc:
        raise gr.Error(str(exc)) from exc


def create_app():
    with gr.Blocks(title="DomainWrap") as app:
        gr.Markdown("# DomainWrap\nBuild a computational boundary around an STL or VTP model.")
        source = gr.File(label="Surface (.stl or .vtp)", file_types=[".stl", ".vtp"], type="filepath")
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Boundary widgets\nDrag a slider to move that face of the domain box.")
                controls = [gr.Slider(label=label, value=value, minimum=0,
                                      maximum=10000, step=1) for label, value in (
                    ("−X", 500), ("+X", 2000), ("−Y", 500), ("+Y", 500),
                    ("−Z", 50), ("+Z", 800))]
                subtract = gr.Checkbox(label="Subtract model (fluid cavity)", value=False)
                fmt = gr.Radio(["stl", "vtp"], value="vtp", label="Output format")
                run = gr.Button("Generate domain", variant="primary")
                download = gr.File(label="Download domain")
            with gr.Column(scale=2):
                viewport = gr.Model3D(label="Interactive domain preview", height=550)
        report = gr.Textbox(label="Bounds and warnings", lines=4)
        inputs = [source, *controls, subtract, fmt]
        outputs = [viewport, download, report]
        run.click(build, inputs=inputs, outputs=outputs)
        source.change(build, inputs=inputs, outputs=outputs)
        for control in controls:
            control.release(build, inputs=inputs, outputs=outputs)
        subtract.change(build, inputs=inputs, outputs=outputs)
        fmt.change(build, inputs=inputs, outputs=outputs)
    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    create_app().launch(server_name=args.host, server_port=args.port)


if __name__ == "__main__":
    main()
