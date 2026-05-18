from pathlib import Path

from scope_modeler.inputs import load_manifest
from scope_modeler.models.enums import CaptureType, Modality


MANIFEST_PATH = Path("data/input/manifest.json")


def test_input_manifest_loads_successfully():
    manifest = load_manifest(MANIFEST_PATH)

    assert manifest.job_id == "wine_bar_staff_showers_001"
    assert len(manifest.captures) == 8
    assert manifest.missing_local_files() == []


def test_all_capture_ids_are_unique():
    manifest = load_manifest(MANIFEST_PATH)
    capture_ids = [capture.capture_id for capture in manifest.captures]

    assert len(capture_ids) == len(set(capture_ids))


def test_expected_capture_ids_exist():
    manifest = load_manifest(MANIFEST_PATH)
    expected_ids = {
        "text_note_001",
        "drawing_floor_plan_001",
        "photo_001",
        "photo_002",
        "photo_003",
        "photo_004",
        "photo_005",
        "audio_mock_001",
    }

    assert {capture.capture_id for capture in manifest.captures} == expected_ids


def test_text_note_points_to_customer_text_file():
    manifest = load_manifest(MANIFEST_PATH)
    text_capture = manifest.get_capture("text_note_001")

    assert text_capture is not None
    assert text_capture.path == Path("data/input/customer_text_fr.txt")


def test_drawing_capture_type_and_modality():
    manifest = load_manifest(MANIFEST_PATH)
    drawing = manifest.get_capture("drawing_floor_plan_001")

    assert drawing is not None
    assert drawing.capture_type == CaptureType.FLOOR_PLAN
    assert drawing.modality == Modality.DRAWING


def test_photo_captures_type_and_modality():
    manifest = load_manifest(MANIFEST_PATH)
    photos = manifest.captures_by_modality(Modality.PHOTO)

    assert len(photos) == 5
    assert all(photo.capture_type == CaptureType.SITE_PHOTO for photo in photos)
    assert all(photo.modality == Modality.PHOTO for photo in photos)


def test_audio_capture_type_and_modality():
    manifest = load_manifest(MANIFEST_PATH)
    audio = manifest.get_capture("audio_mock_001")

    assert audio is not None
    assert audio.capture_type == CaptureType.AUDIO_RECORDING
    assert audio.modality == Modality.AUDIO
