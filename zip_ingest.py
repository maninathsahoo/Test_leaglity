import hashlib
import os
import zipfile
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage

from extensions import db
from models import Batch, BatchStatus, Document, DocumentStatus


class ZipValidationError(Exception):
    def __init__(self, message: str, code: str = "invalid_zip"):
        super().__init__(message)
        self.code = code


def _safe_member_name(name: str) -> bool:
    normalized = os.path.normpath(name)
    if normalized.startswith("..") or os.path.isabs(normalized):
        return False
    if normalized.startswith("/") or "\\" in normalized:
        return False
    return True


def _is_document_entry(name: str, allowed: frozenset[str]) -> bool:
    if name.endswith("/"):
        return False
    suffix = Path(name).suffix.lower()
    return suffix in allowed


def validate_and_list_members(zip_path: Path) -> list[zipfile.ZipInfo]:
    max_docs = current_app.config["MAX_DOCUMENTS_PER_ZIP"]
    max_bytes = current_app.config["MAX_DOCUMENT_BYTES"]
    allowed = current_app.config["ALLOWED_EXTENSIONS"]

    try:
        zf = zipfile.ZipFile(zip_path, "r")
    except zipfile.BadZipFile as exc:
        raise ZipValidationError("Invalid ZIP file", "bad_zip") from exc

    with zf:
        members = []
        for info in zf.infolist():
            if not _safe_member_name(info.filename):
                raise ZipValidationError(
                    f"Unsafe path in archive: {info.filename}",
                    "path_traversal",
                )
            if not _is_document_entry(info.filename, allowed):
                continue
            if info.file_size > max_bytes:
                raise ZipValidationError(
                    f"File exceeds {max_bytes} bytes: {info.filename}",
                    "file_too_large",
                )
            members.append(info)

        if len(members) > max_docs:
            raise ZipValidationError(
                f"ZIP contains more than {max_docs} documents",
                "too_many_documents",
            )
        if not members:
            raise ZipValidationError(
                "No supported documents found in ZIP",
                "no_documents",
            )
        return members


def ingest_zip(
    zip_storage: FileStorage,
    variables: list[str],
) -> Batch:
    if not variables:
        raise ZipValidationError("At least one variable is required", "missing_variables")

    upload_root: Path = current_app.config["UPLOAD_ROOT"]
    upload_root.mkdir(parents=True, exist_ok=True)
    staging_dir = upload_root / "_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    temp_zip = staging_dir / f"upload_{os.urandom(8).hex()}.zip"
    zip_storage.save(temp_zip)

    try:
        members = validate_and_list_members(temp_zip)
    except ZipValidationError:
        temp_zip.unlink(missing_ok=True)
        raise

    batch = Batch(variables=variables, status=BatchStatus.PENDING.value)
    db.session.add(batch)
    db.session.flush()

    batch_dir = upload_root / str(batch.id)
    batch_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(temp_zip, "r") as zf:
        for info in members:
            dest_name = Path(info.filename).name
            dest_path = batch_dir / dest_name
            with zf.open(info, "r") as src, open(dest_path, "wb") as dst:
                dst.write(src.read())

            idem = hashlib.sha256(f"{batch.id}:{dest_name}".encode()).hexdigest()
            doc = Document(
                batch_id=batch.id,
                filename=dest_name,
                storage_path=str(dest_path),
                size_bytes=info.file_size,
                status=DocumentStatus.PENDING.value,
                idempotency_key=idem,
            )
            db.session.add(doc)

    temp_zip.unlink(missing_ok=True)
    batch.status = BatchStatus.PROCESSING.value
    db.session.commit()
    return batch
