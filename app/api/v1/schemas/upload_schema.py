from pydantic import BaseModel, Field


class ProfileImageUploadResponse(BaseModel):
    image_url: str = Field(..., max_length=1024, description="URL of uploaded profile image")


class ClubPositionAttachmentUploadResponse(BaseModel):
    kind: str = Field(..., description="image | certificate")
    path: str = Field(..., max_length=1024, description="path ใต้ uploads/ สำหรับบันทึกลง club_positions[].image_path / certificate_path")
    url: str = Field(..., max_length=1024, description="URL สำหรับเปิดไฟล์ (relative: /uploads/...)")
