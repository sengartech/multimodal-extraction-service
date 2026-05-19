import pytest

from scope_modeler.cli import main


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
