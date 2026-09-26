import pytest

from app.core.exceptions import ValidationError
from app.utils.file_utils import (
    generate_evidence_number,
    generate_stored_filename,
    human_size,
    sanitize_original_filename,
    validate_extension,
    validate_mime_type,
)


def test_sanitize_strips_path_components():
    assert sanitize_original_filename("../../etc/passwd") == "passwd"
    assert sanitize_original_filename("..\\..\\evil.mp4") == "evil.mp4"
    assert sanitize_original_filename("C:\\Windows\\System32\\clip.mp4") == "clip.mp4"


def test_sanitize_rejects_invalid_names():
    with pytest.raises(ValidationError):
        sanitize_original_filename("")
    with pytest.raises(ValidationError):
        sanitize_original_filename("..")
    with pytest.raises(ValidationError):
        sanitize_original_filename(".")


def test_validate_extension_allowlist():
    assert validate_extension("clip.mp4") == ".mp4"
    with pytest.raises(ValidationError):
        validate_extension("clip.exe")
    with pytest.raises(ValidationError):
        validate_extension("clip.txt")


def test_validate_mime_type_allowlist():
    assert validate_mime_type("video/mp4") is None
    assert validate_mime_type("video/x-matroska") is None
    with pytest.raises(ValidationError):
        validate_mime_type("text/plain")
    with pytest.raises(ValidationError):
        validate_mime_type(None)


def test_generate_stored_filename_is_unique_and_safe():
    first = generate_stored_filename(".mp4")
    second = generate_stored_filename(".mp4")
    assert first != second
    assert first.endswith(".mp4")
    assert ".." not in first


def test_generate_evidence_number_format():
    number = generate_evidence_number()
    assert number.startswith("EVD-")
    assert len(number.split("-")) == 3


def test_human_size_formatting():
    assert human_size(0) == "0 B"
    assert human_size(1024) == "1.0 KB"
    assert human_size(1536) == "1.5 KB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"
