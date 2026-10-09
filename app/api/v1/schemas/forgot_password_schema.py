from datetime import date

from pydantic import BaseModel, Field, field_validator


class ForgotPasswordVerifyRequest(BaseModel):
    citizen_id: str = Field(min_length=13, max_length=13)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birth_date: date  # ค.ศ. YYYY-MM-DD

    @field_validator("citizen_id")
    @classmethod
    def _digits_only(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("citizen_id must be 13 digits")
        return value


class ForgotPasswordVerifyResponse(BaseModel):
    reset_token: str
    expires_in: int


class ForgotPasswordResetRequest(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def _passwords_match(cls, value: str, info) -> str:
        if value != info.data.get("new_password"):
            raise ValueError("password_mismatch")
        return value


class ForgotPasswordResetResponse(BaseModel):
    success: bool = True
    message: str = "password_reset_success"
