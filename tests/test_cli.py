import json
from pathlib import Path

import pytest

from scope_modeler.cli import load_extractor_result, load_extractor_results, main
from scope_modeler.extractors import ExtractorResult
from scope_modeler.models import Modality


def test_extract_vision_requires_capture_id():
    with pytest.raises(SystemExit) as exc:
        main(["extract-vision", "--output", "data/output/vision.json"])

    assert exc.value.code == 2


def test_extract_vision_errors_for_missing_capture():
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "extract-vision",
                "--capture-id",
                "missing_capture",
                "--output",
                "data/output/vision.json",
            ]
        )

    assert exc.value.code == 2


def test_extract_vision_errors_for_non_photo_capture():
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "extract-vision",
                "--capture-id",
                "text_note_001",
                "--output",
                "data/output/vision.json",
            ]
        )

    assert exc.value.code == 2


def test_extract_text_requires_capture_id():
    with pytest.raises(SystemExit) as exc:
        main(["extract-text", "--output", "data/output/text.json"])

    assert exc.value.code == 2


def test_extract_text_errors_for_missing_capture():
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "extract-text",
                "--capture-id",
                "missing_capture",
                "--output",
                "data/output/text.json",
            ]
        )

    assert exc.value.code == 2


def test_extract_text_errors_for_non_text_capture():
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "extract-text",
                "--capture-id",
                "photo_001",
                "--output",
                "data/output/text.json",
            ]
        )

    assert exc.value.code == 2


def test_extract_drawing_errors_for_non_drawing_capture():
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "extract-drawing",
                "--capture-id",
                "photo_001",
                "--output",
                "data/output/drawing.json",
            ]
        )

    assert exc.value.code == 2


def test_load_extractor_result_from_json_file(tmp_path):
    path = tmp_path / "extractor_result.json"
    path.write_text(
        json.dumps(
            {
                "capture_id": "text_note_001",
                "extractor_name": "test_extractor",
                "modality": "text",
                "observations": [],
                "candidate_tasks": [],
                "candidate_materials": [],
                "assumptions": [],
                "clarifying_questions": [],
                "confidence": 0.8,
                "raw_output": {},
            }
        ),
        encoding="utf-8",
    )

    result = load_extractor_result(path)

    assert isinstance(result, ExtractorResult)
    assert result.capture_id == "text_note_001"
    assert result.modality == Modality.TEXT


def test_load_extractor_results_from_json_files(tmp_path):
    first = _write_extractor_result(tmp_path / "first.json", "text_note_001", "text")
    second = _write_extractor_result(tmp_path / "second.json", "photo_001", "photo")

    results = load_extractor_results([first, second])

    assert [result.capture_id for result in results] == ["text_note_001", "photo_001"]


def test_build_scope_errors_for_missing_extractor_output():
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "build-scope",
                "--text-output",
                "data/output/does_not_exist.json",
                "--drawing-output",
                "data/output/drawing_result.json",
                "--vision-output",
                "data/output/vision_photo_01.json",
            ]
        )

    assert exc.value.code == 2


def _write_extractor_result(path: Path, capture_id: str, modality: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "capture_id": capture_id,
                "extractor_name": "test_extractor",
                "modality": modality,
                "observations": [],
                "candidate_tasks": [],
                "candidate_materials": [],
                "assumptions": [],
                "clarifying_questions": [],
                "confidence": 0.8,
                "raw_output": {},
            }
        ),
        encoding="utf-8",
    )
    return path
