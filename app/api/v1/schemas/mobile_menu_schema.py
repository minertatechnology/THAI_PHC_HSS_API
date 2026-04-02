from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

MobileMenuOpenType = Literal["webview", "external", "deeplink", "native"]


class MobileMenuBase(BaseModel):
    menu_key: str = Field(..., max_length=100, description="Unique key used by the mobile client to map menu actions.")
    menu_name: str = Field(..., max_length=255, description="Display name of the menu item.")
    menu_description: Optional[str] = Field(default=None, description="Optional helper text or subtitle for the menu.")
    icon_name: Optional[str] = Field(default=None, max_length=255, description="Optional icon identifier or asset name.")
    open_type: MobileMenuOpenType = Field(default="webview", description="How the app should open this menu (webview/external/deeplink/native).")
    webview_title: Optional[str] = Field(default=None, max_length=255, description="Title for in-app webview (required when open_type=webview).")
    webview_url: Optional[str] = Field(default=None, max_length=512, description="URL loaded inside in-app webview.")
    redirect_url: Optional[str] = Field(default=None, max_length=512, description="URL opened via external browser when open_type=external.")
    deeplink_url: Optional[str] = Field(default=None, max_length=512, description="Deep link URI handled by the native app when open_type=deeplink.")
    allowed_user_types: List[str] = Field(default_factory=list, description="Restrict visibility to specific user types (empty = all).")
    platforms: List[str] = Field(default_factory=list, description="Restrict visibility by platform (android/ios/web). Empty = all.")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Arbitrary JSON metadata for future use.")
    display_order: int = Field(default=0, ge=0, description="Sorting order; lower numbers appear first.")
    is_active: bool = Field(default=True, description="Set false to hide the menu without deleting it.")


class MobileMenuCreate(MobileMenuBase):
    pass


class MobileMenuUpdate(BaseModel):
    menu_key: Optional[str] = Field(default=None, max_length=100)
    menu_name: Optional[str] = Field(default=None, max_length=255)
    menu_description: Optional[str] = Field(default=None)
    icon_name: Optional[str] = Field(default=None, max_length=255)
    open_type: Optional[MobileMenuOpenType] = None
    webview_title: Optional[str] = Field(default=None, max_length=255)
    webview_url: Optional[str] = Field(default=None, max_length=512)
    redirect_url: Optional[str] = Field(default=None, max_length=512)
    deeplink_url: Optional[str] = Field(default=None, max_length=512)
    allowed_user_types: Optional[List[str]] = None
    platforms: Optional[List[str]] = None
    metadata: Optional[dict[str, Any]] = None
    display_order: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class MobileMenuResponse(MobileMenuBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    class Config:
        from_attributes = True
