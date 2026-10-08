from fastapi import APIRouter, Request

from app.api.v1.schemas.forgot_password_schema import (
    ForgotPasswordResetRequest,
    ForgotPasswordResetResponse,
    ForgotPasswordVerifyRequest,
    ForgotPasswordVerifyResponse,
)
from app.services.forgot_password_service import ForgotPasswordService
from app.utils.thaid_utils import extract_request_metadata

forgot_password_router = APIRouter(prefix="/auth/forgot-password", tags=["auth"])


@forgot_password_router.post("/verify", response_model=ForgotPasswordVerifyResponse)
async def forgot_password_verify(payload: ForgotPasswordVerifyRequest, request: Request):
    ip = extract_request_metadata(request).get("ip")
    return await ForgotPasswordService.verify(payload.citizen_id, payload.birth_date, ip)


@forgot_password_router.post("/reset", response_model=ForgotPasswordResetResponse)
async def forgot_password_reset(payload: ForgotPasswordResetRequest, request: Request):
    ip = extract_request_metadata(request).get("ip")
    return await ForgotPasswordService.reset(payload.reset_token, payload.new_password, ip)
