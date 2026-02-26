"""
Authentication Endpoints - WebAuthn Passkey-Only Auth.

Flow:
1. POST /register/begin    → Generate registration challenge
2. POST /register/complete → Verify attestation, create user + passkey, return JWT
3. POST /login/begin       → Generate authentication challenge  
4. POST /login/complete    → Verify assertion, return JWT
5. POST /refresh           → Refresh access token
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import create_token_pair, verify_token
from backend.schemas.auth import (
    RegistrationBeginRequest,
    RegistrationBeginResponse,
    RegistrationCompleteRequest,
    AuthenticationBeginRequest,
    AuthenticationBeginResponse,
    AuthenticationCompleteRequest,
    AuthResponse,
    RefreshRequest,
)
from backend.services.auth_service import AuthService

router = APIRouter()


@router.post("/register/begin", response_model=RegistrationBeginResponse)
async def registration_begin(
    request: RegistrationBeginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate WebAuthn registration challenge.
    
    Returns publicKeyCredentialCreationOptions for the browser's
    navigator.credentials.create() API.
    """
    service = AuthService(db)
    options = await service.begin_registration(
        username=request.username,
        display_name=request.display_name,
        email=request.email,
    )
    return RegistrationBeginResponse(options=options)


@router.post("/register/complete", response_model=AuthResponse)
async def registration_complete(
    request: RegistrationCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify WebAuthn attestation and create user.
    
    Validates the authenticator's response, stores the public key credential,
    creates the user, initializes gamification state, and returns JWT token pair.
    """
    service = AuthService(db)
    user = await service.complete_registration(
        credential=request.credential,
        challenge_id=request.challenge_id,
    )
    tokens = create_token_pair(str(user.id))
    return AuthResponse(
        user_id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        tokens=tokens,
    )


@router.post("/login/begin", response_model=AuthenticationBeginResponse)
async def login_begin(
    request: AuthenticationBeginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate WebAuthn authentication challenge.
    
    Returns publicKeyCredentialRequestOptions for the browser's
    navigator.credentials.get() API.
    """
    service = AuthService(db)
    options = await service.begin_authentication(username=request.username)
    return AuthenticationBeginResponse(options=options)


@router.post("/login/complete", response_model=AuthResponse)
async def login_complete(
    request: AuthenticationCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify WebAuthn assertion and issue JWT.
    
    Validates the authenticator's signature against stored public key,
    updates sign count, refreshes streak, and returns JWT token pair.
    """
    service = AuthService(db)
    user = await service.complete_authentication(
        credential=request.credential,
        challenge_id=request.challenge_id,
    )
    tokens = create_token_pair(str(user.id))
    return AuthResponse(
        user_id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        tokens=tokens,
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    token_data = verify_token(request.refresh_token, expected_type="refresh")
    service = AuthService(db)
    user = await service.get_user_by_id(token_data.sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    tokens = create_token_pair(str(user.id))
    return AuthResponse(
        user_id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        tokens=tokens,
    )
