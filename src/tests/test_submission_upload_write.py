from io import BytesIO

import pytest
from fastapi import HTTPException

from kedro_graphql.asgi import _write_uploaded_file


def test_upload_writes_complete_file_and_retries_atomically(tmp_path):
    path = tmp_path / "nested" / "file.txt"
    _write_uploaded_file(BytesIO(b"abc"), path, 10, 3)
    assert path.read_bytes() == b"abc"
    _write_uploaded_file(BytesIO(b"xyz"), path, 10, 3)
    assert path.read_bytes() == b"xyz"
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize("content,max_bytes,expected", [(b"abc", 2, None), (b"abc", 10, 2), (b"a", 10, 2)])
def test_failed_upload_never_replaces_existing_file(tmp_path, content, max_bytes, expected):
    path = tmp_path / "file.txt"
    path.write_bytes(b"previous")
    with pytest.raises(HTTPException):
        _write_uploaded_file(BytesIO(content), path, max_bytes, expected)
    assert path.read_bytes() == b"previous"
    assert list(tmp_path.iterdir()) == [path]


def test_interrupted_upload_removes_temporary_file(tmp_path):
    path = tmp_path / "file.txt"
    class BrokenSource:
        def read(self, size):
            raise OSError("connection lost")
    with pytest.raises(OSError):
        _write_uploaded_file(BrokenSource(), path, 10, 3)
    assert not list(tmp_path.iterdir())
