import hashlib
import re
from pathlib import Path
from uuid import uuid4

from docx import Document
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.core.config import get_settings

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    ".txt": {"text/plain", "application/octet-stream"},
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
    ext = storage_path.suffix.lower()
    if ext == ".pdf":
        try:
            reader = PdfReader(storage_path)
            pages_text = []
            for idx, page in enumerate(reader.pages, start=1):
                p_text = (page.extract_text() or "").strip()
                if p_text:
                    pages_text.append(f"[Page {idx}]\n{p_text}")
            text = "\n\n".join(pages_text)
            if not text.strip() and len(reader.pages) > 0:
                raise ValueError("Scanned PDF detected without extractable text layer. OCR required.")
        except Exception as exc:
            if "Scanned PDF" in str(exc):
                raise
            raise ValueError(f"Corrupted or unreadable PDF document: {exc}") from exc
    elif ext == ".docx":
        try:
            document = Document(storage_path)
            text = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
        except Exception as exc:
            raise ValueError(f"Corrupted or unreadable DOCX document: {exc}") from exc
    elif ext == ".txt":
        try:
            text = storage_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            raise ValueError(f"Failed to read text file: {exc}") from exc
    else:
        raise ValueError(f"Unsupported document format: {ext}")

    if not text.strip():
        raise ValueError("Document contains no readable text")
    return text[:100_000]
