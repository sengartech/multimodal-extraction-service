"""Local CLI entrypoint for the scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scope_modeler import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scope-modeler",
        description="Local-first renovation scope extraction scaffold.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    extract_vision = subparsers.add_parser(
        "extract-vision",
        help="Run OpenAI-backed vision extraction for one photo capture.",
    )
    extract_vision.add_argument(
        "--manifest",
        default="data/input/manifest.json",
        help="Path to the input manifest.",
    )
    extract_vision.add_argument(
        "--capture-id",
        required=True,
        help="Photo capture ID to extract.",
    )
    extract_vision.add_argument(
        "--output",
        required=True,
        help="Path where the extracted JSON result should be written.",
    )
    extract_vision.set_defaults(handler=run_extract_vision)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args, parser)


def run_extract_vision(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    from dotenv import load_dotenv

    from scope_modeler.extractors import OpenAIVisionModelClient, VisionExtractor
    from scope_modeler.inputs import load_manifest
    from scope_modeler.models import Modality

    load_dotenv()
    manifest = load_manifest(args.manifest)
    capture = manifest.get_capture(args.capture_id)
    if capture is None:
        parser.error(f"Capture not found in manifest: {args.capture_id}")
    if capture.modality != Modality.PHOTO:
        parser.error(
            f"Capture {args.capture_id} has modality {capture.modality}; extract-vision requires photo."
        )

    result = VisionExtractor(OpenAIVisionModelClient()).extract(capture)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return 0
