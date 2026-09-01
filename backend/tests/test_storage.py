import pytest

from app.services.storage import UnsupportedVideoError, validate_filename


@pytest.mark.parametrize("filename", ["match.mp4", "match.MOV", "match.avi", "Match.Mp4"])
def test_validate_filename_accepts_supported_formats(filename):
    assert validate_filename(filename) == f".{filename.rsplit('.', 1)[1].lower()}"


@pytest.mark.parametrize("filename", ["match.mkv", "match.txt", "match", "match.webm"])
def test_validate_filename_rejects_unsupported_formats(filename):
    with pytest.raises(UnsupportedVideoError):
        validate_filename(filename)
