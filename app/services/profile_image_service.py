from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


class ProfileImageService:
    _BASE_UPLOAD_ROOT = Path("uploads") / "profile-images"
    _MAX_FILE_BYTES = 10 * 1024 * 1024
    _ALLOWED_CONTEXTS = {
        "osm": "osm",
        "yuwa_osm": "yuwa-osm",
        "officer": "officer",
        "people": "people",
    }

    @classmethod
    async def upload_profile_image(cls, *, file: UploadFile, context: str) -> str:
        folder = cls._resolve_context_folder(context)
        stored_path = await cls._store_image(file, folder)
        return stored_path

    @classmethod
    def _resolve_context_folder(cls, context: str) -> str:
        key = str(context or "").strip().lower()
        if key not in cls._ALLOWED_CONTEXTS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_profile_image_context")
        return cls._ALLOWED_CONTEXTS[key]

    @classmethod
    async def _store_image(cls, upload: UploadFile, folder: str) -> str:
        if upload is None or not getattr(upload, "filename", None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_image")
        content_type = (upload.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_image_type")

        raw_bytes = await upload.read()
        if len(raw_bytes) > cls._MAX_FILE_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="image_too_large")
        if not raw_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_image")

        suffix = cls._resolve_suffix(upload.filename, content_type)
        filename = f"{uuid4()}{suffix}"
        destination = cls._ensure_upload_path(folder) / filename
        await asyncio.to_thread(destination.write_bytes, raw_bytes)
        await upload.close()
        return str(destination.as_posix())

    @staticmethod
    def _resolve_suffix(original_name: str | None, content_type: str) -> str:
        if original_name:
            suffix = Path(original_name).suffix.lower()
            if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}:
                return suffix
        guessed = mimetypes.guess_extension(content_type) or ".jpg"
        normalized = guessed.lower()
        if normalized == ".jpe":
            normalized = ".jpg"
        return normalized

    @classmethod
    def _ensure_upload_path(cls, folder: str) -> Path:
        target = cls._BASE_UPLOAD_ROOT / folder
        target.mkdir(parents=True, exist_ok=True)
        return target
