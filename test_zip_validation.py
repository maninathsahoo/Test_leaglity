import zipfile

import pytest

from zip_ingest import ZipValidationError, validate_and_list_members


def test_rejects_path_traversal(app, tmp_path):
    zpath = tmp_path / "bad.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("../evil.txt", b"data")
    with app.app_context():
        with pytest.raises(ZipValidationError) as exc:
            validate_and_list_members(zpath)
        assert exc.value.code == "path_traversal"


def test_rejects_file_too_large(app, tmp_path):
    zpath = tmp_path / "big.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("big.pdf", b"x" * (15 * 1024 * 1024 + 1))
    with app.app_context():
        with pytest.raises(ZipValidationError) as exc:
            validate_and_list_members(zpath)
        assert exc.value.code == "file_too_large"


def test_rejects_too_many_documents(app, tmp_path):
    zpath = tmp_path / "many.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for i in range(1001):
            zf.writestr(f"doc{i}.txt", b"ok")
    with app.app_context():
        with pytest.raises(ZipValidationError) as exc:
            validate_and_list_members(zpath)
        assert exc.value.code == "too_many_documents"


def test_rejects_bad_zip(app, tmp_path):
    zpath = tmp_path / "notzip.zip"
    zpath.write_bytes(b"not a zip")
    with app.app_context():
        with pytest.raises(ZipValidationError) as exc:
            validate_and_list_members(zpath)
        assert exc.value.code == "bad_zip"
