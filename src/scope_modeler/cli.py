"""Local CLI entrypoint for the scaffold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scope_modeler import __version__
from scope_modeler.extractors import ExtractorResult


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
    extract_text = subparsers.add_parser(
        "extract-text",
        help="Run OpenAI-backed text extraction for one text capture.",
    )
    extract_text.add_argument(
        "--manifest",
        default="data/input/manifest.json",
        help="Path to the input manifest.",
    )
    extract_text.add_argument(
        "--capture-id",
        required=True,
        help="Text capture ID to extract.",
    )
    extract_text.add_argument(
        "--output",
        required=True,
        help="Path where the extracted JSON result should be written.",
    )
    extract_text.set_defaults(handler=run_extract_text)
    extract_drawing = subparsers.add_parser(
        "extract-drawing",
        help="Run OpenAI-backed two-pass drawing extraction for one drawing capture.",
    )
    extract_drawing.add_argument(
        "--manifest",
        default="data/input/manifest.json",
        help="Path to the input manifest.",
    )
    extract_drawing.add_argument(
        "--capture-id",
        required=True,
        help="Drawing capture ID to extract.",
    )
    extract_drawing.add_argument(
        "--output",
        required=True,
        help="Path where the extracted JSON result should be written.",
    )
    extract_drawing.set_defaults(handler=run_extract_drawing)
    build_scope = subparsers.add_parser(
        "build-scope",
        help="Fuse saved extractor outputs into a final ScopeBrief.",
    )
    build_scope.add_argument(
        "--manifest",
        default="data/input/manifest.json",
        help="Path to the input manifest.",
    )
    build_scope.add_argument(
        "--text-output",
        default="data/output/text_note_001.json",
        help="Saved text ExtractorResult JSON.",
    )
    build_scope.add_argument(
        "--drawing-output",
        default="data/output/drawing_result.json",
        help="Saved drawing ExtractorResult JSON.",
    )
    build_scope.add_argument(
        "--vision-output",
        action="append",
        default=None,
        help="Saved vision ExtractorResult JSON. Repeat for multiple files.",
    )
    build_scope.add_argument(
        "--output",
        default="data/output/scope_brief.json",
        help="Path where the final ScopeBrief JSON should be written.",
    )
    build_scope.set_defaults(handler=run_build_scope)
    eval_scope = subparsers.add_parser(
        "eval-scope",
        help="Run deterministic assertions against a ScopeBrief JSON.",
    )
    eval_scope.add_argument(
        "--scope",
        default="data/output/scope_brief.json",
        help="Path to ScopeBrief JSON.",
    )
    eval_scope.add_argument(
        "--output",
        default="data/output/eval_results.json",
        help="Path where EvalReport JSON should be written.",
    )
    eval_scope.set_defaults(handler=run_eval_scope)
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
    from scope_modeler.extractors import OpenAIVisionModelClient, VisionExtractor
    from scope_modeler.inputs import load_manifest
    from scope_modeler.models import Modality

    load_env()
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


def run_extract_text(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    from scope_modeler.extractors import LLMTextExtractor, OpenAITextModelClient
    from scope_modeler.inputs import load_manifest
    from scope_modeler.models import Modality

    load_env()
    manifest = load_manifest(args.manifest)
    capture = manifest.get_capture(args.capture_id)
    if capture is None:
        parser.error(f"Capture not found in manifest: {args.capture_id}")
    if capture.modality != Modality.TEXT:
        parser.error(
            f"Capture {args.capture_id} has modality {capture.modality}; extract-text requires text."
        )

    result = LLMTextExtractor(OpenAITextModelClient()).extract(capture)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote text extraction result to {output_path}")
    return 0


def run_extract_drawing(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    from scope_modeler.extractors import (
        OpenAIDrawingGeometryClient,
        OpenAIDrawingSemanticClient,
        OpenAITwoPassDrawingParser,
    )
    from scope_modeler.inputs import load_manifest
    from scope_modeler.models import Modality

    load_env()
    manifest = load_manifest(args.manifest)
    capture = manifest.get_capture(args.capture_id)
    if capture is None:
        parser.error(f"Capture not found in manifest: {args.capture_id}")
    if capture.modality != Modality.DRAWING:
        parser.error(
            f"Capture {args.capture_id} has modality {capture.modality}; extract-drawing requires drawing."
        )

    result = OpenAITwoPassDrawingParser(
        geometry_client=OpenAIDrawingGeometryClient(),
        semantic_client=OpenAIDrawingSemanticClient(),
    ).extract(capture)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote drawing extraction result to {output_path}")
    return 0


def run_build_scope(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    vision_outputs = args.vision_output or [
        "data/output/vision_photo_01.json",
        "data/output/vision_photo_02.json",
    ]
    result_paths = [
        Path(args.text_output),
        Path(args.drawing_output),
        *[Path(path) for path in vision_outputs],
    ]
    for result_path in result_paths:
        if not result_path.exists():
            parser.error(f"Extractor output file not found: {result_path}")

    from scope_modeler.fusion import FusionEngine, OpenAIFusionModelClient
    from scope_modeler.inputs import load_manifest
    from scope_modeler.models import GapSeverity, SourceCapture

    load_env()
    manifest = load_manifest(args.manifest)
    source_captures = [
        SourceCapture(
            capture_id=capture.capture_id,
            capture_type=capture.capture_type,
            modality=capture.modality,
            path=str(capture.path),
            description=capture.description,
            language=capture.language,
        )
        for capture in manifest.captures
    ]
    extractor_results = load_extractor_results(result_paths)

    scope = FusionEngine(OpenAIFusionModelClient()).fuse(
        job_id=manifest.job_id,
        source_captures=source_captures,
        extractor_results=extractor_results,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(scope.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    pricing_ready = (
        scope.pricing_readiness.pricing_ready
        if scope.pricing_readiness is not None
        else False
    )
    must_have_count = sum(
        1 for question in scope.clarifying_questions if question.severity == GapSeverity.MUST_HAVE
    )
    print(
        f"Wrote scope brief to {output_path} "
        f"(pricing_ready={pricing_ready}, tasks={len(scope.tasks)}, must_have_questions={must_have_count})"
    )
    return 0


def load_extractor_result(path: Path) -> "ExtractorResult":
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return ExtractorResult.model_validate(data)


def load_extractor_results(paths: list[Path]) -> list["ExtractorResult"]:
    return [load_extractor_result(path) for path in paths]


def run_eval_scope(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    from scope_modeler.eval.harness import evaluate_scope
    from scope_modeler.models import ScopeBrief

    scope_path = Path(args.scope)
    if not scope_path.exists():
        parser.error(f"ScopeBrief file not found: {scope_path}")
    with scope_path.open("r", encoding="utf-8") as file:
        scope_data = json.load(file)
    scope_data.pop("ordered_task_ids", None)
    scope = ScopeBrief.model_validate(scope_data)
    report = evaluate_scope(scope, str(scope_path))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        f"Eval precision={report.overall_precision:.2f} recall={report.overall_recall:.2f} "
        f"passed={report.passed} failed={report.failed} partial={report.partial}"
    )
    return 0


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    load_dotenv()
