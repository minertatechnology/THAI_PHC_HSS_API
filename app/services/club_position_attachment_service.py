from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


class ClubPositionAttachmentService:
    """เก็บไฟล์แนบของตำแหน่งชมรม อสม. (รูปภาพ / หนังสือรับรอง)

    เก็บใต้ uploads/osm-club-positions/<kind>/ เพื่อให้ static mount /uploads เสิร์ฟได้
    เหมือนรูปโปรไฟล์ (ดู ProfileImageService) — path ที่คืนไปจะถูกบันทึกลง
    osm_profile_club_positions.image_path / certificate_path ตอน create/update โปรไฟล์
    """

    _BASE_UPLOAD_ROOT = Path("uploads") / "osm-club-positions"
    _MAX_FILE_BYTES = 10 * 1024 * 1024

    # kind -> (โฟลเดอร์, content-type ที่รับ, นามสกุลที่รับ)
    _KINDS = {
        "image": (
            "images",
            {"image/jpeg", "image/png", "image/webp"},
            {".jpg", ".jpeg", ".png", ".webp"},
        ),
        "certificate": (
            "certificates",
            {"application/pdf", "image/jpeg", "image/png", "image/webp"},
            {".pdf", ".jpg", ".jpeg", ".png", ".webp"},
        ),
    }

    @classmethod
    async def upload(cls, *, file: UploadFile, kind: str) -> str:
        key = str(kind or "").strip().lower()
        if key not in cls._KINDS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_attachment_kind")
        folder, allowed_types, allowed_suffixes = cls._KINDS[key]

        if file is None or not getattr(file, "filename", None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_file")

        content_type = (file.content_type or "").lower()
        suffix = Path(file.filename).suffix.lower()
        if content_type not in allowed_types and suffix not in allowed_suffixes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_file_type")

        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_file")
        if len(raw_bytes) > cls._MAX_FILE_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="file_too_large")

        if suffix not in allowed_suffixes:
            guessed = (mimetypes.guess_extension(content_type) or "").lower()
            suffix = ".jpg" if guessed in {"", ".jpe"} else guessed

        target_dir = cls._BASE_UPLOAD_ROOT / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / f"{uuid4()}{suffix}"
        await asyncio.to_thread(destination.write_bytes, raw_bytes)
        await file.close()
        return destination.as_posix()
