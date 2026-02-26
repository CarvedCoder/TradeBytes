"""
Auth Schemas - WebAuthn request/response models.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from backend.core.security import TokenPair


class RegistrationBeginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    display_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)


class RegistrationBeginResponse(BaseModel):
    options: dict  # PublicKeyCredentialCreationOptions (JSON-serialized)
    challenge_id: str | None = None


class RegistrationCompleteRequest(BaseModel):
    credential: dict  # AuthenticatorAttestationResponse
    challenge_id: str


class AuthenticationBeginRequest(BaseModel):
    username: str


class AuthenticationBeginResponse(BaseModel):
    options: dict  # PublicKeyCredentialRequestOptions (JSON-serialized)
    challenge_id: str | None = None


class AuthenticationCompleteRequest(BaseModel):
    credential: dict  # AuthenticatorAssertionResponse
    challenge_id: str


class AuthResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    tokens: TokenPair


class RefreshRequest(BaseModel):
    refresh_token: str
