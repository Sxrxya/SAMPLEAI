import hashlib
import re
from pathlib import Path
from uuid import uuid4

from docx import Document
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.core.config import get_settings

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
}


def safe_filename(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(value).name).strip("._")
    return (normalized or "upload")[:180]


async def store_upload(upload: UploadFile, owner_id: str) -> tuple[str, str, int, str, str]:
    original_name = safe_filename(upload.filename or "resume")
    extension = Path(original_name).suffix.lower()
    if (
        extension not in ALLOWED_EXTENSIONS
        or upload.content_type not in ALLOWED_MIME_TYPES[extension]
    ):
        raise HTTPException(status_code=415, detail="Only PDF and DOCX files are accepted")

    root = get_settings().storage_root.resolve()
    owner_directory = (root / owner_id).resolve()
    owner_directory.mkdir(parents=True, exist_ok=True)
    storage_key = f"{owner_id}/{uuid4().hex}{extension}"
    destination = (root / storage_key).resolve()
    if root not in destination.parents:
        raise HTTPException(status_code=400, detail="Invalid storage path")
    temporary_path = destination.with_suffix(destination.suffix + ".part")

    digest = hashlib.sha256()
    size = 0
    try:
        with temporary_path.open("xb") as target:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > get_settings().max_upload_bytes:
                    raise HTTPException(status_code=413, detail="File exceeds the upload limit")
                digest.update(chunk)
                target.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        with temporary_path.open("rb") as source:
            signature = source.read(8)
        if extension == ".pdf" and not signature.startswith(b"%PDF-"):
            raise HTTPException(status_code=415, detail="File content is not a valid PDF")
        if extension == ".docx" and not signature.startswith(b"PK"):
            raise HTTPException(status_code=415, detail="File content is not a valid DOCX")
        temporary_path.replace(destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return storage_key, original_name, size, digest.hexdigest(), extension


def extract_text(storage_path: Path) -> str:
    if storage_path.suffix.lower() == ".pdf":
        reader = PdfReader(storage_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        document = Document(storage_path)
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    if not text.strip():
        raise ValueError("No text could be extracted; OCR is not configured")
    return text[:100_000]
