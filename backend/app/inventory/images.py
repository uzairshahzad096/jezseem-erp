"""
Product image storage.

Images live in Cloudflare R2 when it is configured (the hosted server keeps no
files), else on disk under `settings.UPLOAD_DIR`; never in the database: a
photo stored in a row makes every SELECT on inventory_items carry it, and the
Postgres backup grows with the pictures. The row keeps a short relative key
("items/<uuid>.jpg") and the file keeps the bytes.

REQUIRES BUSINESS CONFIRMATION: the accepted formats. JPEG, PNG and WebP
cover phone photos and screenshots, which is what the Add Product form is
for. If the old ERP holds scanned TIFFs or PDFs for items, add them here
rather than letting the upload fail with a format error.

The size ceiling is MAX_UPLOAD_SIZE_MB from .env, not a value invented here.
"""

import uuid
from pathlib import Path

from botocore.exceptions import ClientError
from app.core.r2_storage import get_r2_client

from fastapi import HTTPException, Request, UploadFile

from app.core.config import settings

# Where the static mount in app/main.py exposes UPLOAD_DIR.
MEDIA_URL_PREFIX = "/media"

# Subdirectory of UPLOAD_DIR holding item images.
ITEM_IMAGE_DIR = "items"

# The extension is chosen from the file's own signature, never from the name
# the browser sent: an upload called "photo.png" that is really something else
# is rejected instead of being stored under a name that lies about it.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
)
_EXTENSIONS = {ext for _, ext in _SIGNATURES} | {".webp"}


def _detect_extension(head: bytes) -> str | None:
    """The extension implied by the file's magic bytes, or None if it is not
    an image format we accept."""
    for signature, ext in _SIGNATURES:
        if head.startswith(signature):
            return ext
    # WebP is a RIFF container: "RIFF" <4-byte size> "WEBP".
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


def _item_dir() -> Path:
    return Path(settings.UPLOAD_DIR) / ITEM_IMAGE_DIR


def save_item_image(file: UploadFile, item_id: uuid.UUID) -> str:
    """Validate and store one product image, returning its storage key."""
    return save_image(file, ITEM_IMAGE_DIR, item_id)


def delete_item_image(item_id: uuid.UUID) -> None:
    delete_image(ITEM_IMAGE_DIR, item_id)


CONTENT_TYPES = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def r2_enabled() -> bool:
    """Pictures go to Cloudflare R2 when its settings are present (the hosted
    server keeps no files of its own); otherwise to UPLOAD_DIR on this disk."""
    return all((settings.R2_ACCOUNT_ID, settings.R2_ACCESS_KEY_ID,
                settings.R2_SECRET_ACCESS_KEY, settings.R2_BUCKET_NAME))


def read_image(storage_key: str) -> bytes | None:
    """The stored bytes for a key, or None when there is no such image."""
    if r2_enabled():
        try:
            return get_r2_client().get_object(Bucket=settings.R2_BUCKET_NAME, Key=storage_key)["Body"].read()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
                return None
            raise
    path = Path(settings.UPLOAD_DIR) / storage_key
    return path.read_bytes() if path.is_file() else None


def save_image(file: UploadFile, subdir: str, owner_id: uuid.UUID) -> str:
    """Validate and store one image named after the record that owns it,
    returning its storage key. An image held under another extension is
    removed only after the new one is stored, so a failed upload never leaves
    the record without its old picture."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    data = file.file.read(max_bytes + 1)

    if not data:
        raise HTTPException(400, "The uploaded file is empty.")

    if len(data) > max_bytes:
        raise HTTPException(413, "Image exceeds upload size limit.")

    extension = _detect_extension(data[:16])

    if extension is None:
        raise HTTPException(400, "Unsupported image format.")

    key = f"{subdir}/{owner_id}{extension}"
    if r2_enabled():
        client = get_r2_client()
        try:
            client.put_object(Bucket=settings.R2_BUCKET_NAME, Key=key, Body=data,
                              ContentType=CONTENT_TYPES[extension])
            for old_extension in _EXTENSIONS - {extension}:
                client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=f"{subdir}/{owner_id}{old_extension}")
        except ClientError:
            raise HTTPException(502, "The picture store is not answering. Try again in a minute.")
    else:
        directory = Path(settings.UPLOAD_DIR) / subdir
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{owner_id}{extension}").write_bytes(data)
        for old_extension in _EXTENSIONS - {extension}:
            (directory / f"{owner_id}{old_extension}").unlink(missing_ok=True)
    return key


def delete_image(subdir: str, owner_id: uuid.UUID) -> None:
    """Remove the owner's image, whichever extension it was stored with.
    Silent when there is nothing to remove."""
    if r2_enabled():
        client = get_r2_client()
        for extension in _EXTENSIONS:
            client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=f"{subdir}/{owner_id}{extension}")
        return
    directory = Path(settings.UPLOAD_DIR) / subdir
    for extension in _EXTENSIONS:
        (directory / f"{owner_id}{extension}").unlink(missing_ok=True)


def image_url(request: Request, storage_key: str | None) -> str | None:
    """Absolute URL for a stored image.

    Absolute rather than relative so the browser can drop it straight into an
    <img src>: the frontend runs on a different port from the API and would
    otherwise have to know where media is mounted.
    """
    if not storage_key:
        return None
    return f"{str(request.base_url).rstrip('/')}{MEDIA_URL_PREFIX}/{storage_key}"
