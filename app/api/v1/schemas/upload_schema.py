from pydantic import BaseModel, Field


class ProfileImageUploadResponse(BaseModel):
    image_url: str = Field(..., max_length=1024, description="URL of uploaded profile image")
