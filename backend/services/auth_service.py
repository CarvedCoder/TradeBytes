"""
Authentication Service - WebAuthn Passkey Registration & Verification.

Implements the full WebAuthn ceremony:
1. Generate challenge with user-specific parameters
2. Verify attestation (registration) / assertion (login)
3. Store/verify credentials using cryptographic public keys
4. No passwords ever stored or transmitted
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)

from backend.core.config import get_settings
from backend.models.user import User, Passkey, WebAuthnChallenge
from backend.models.gamification import UserGamification
from backend.models.trading import Portfolio

logger = structlog.get_logger()
settings = get_settings()


class AuthService:
    """Handles WebAuthn registration and authentication ceremonies."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def begin_registration(
        self, username: str, display_name: str, email: str
    ) -> dict[str, Any]:
        """Generate WebAuthn registration options (challenge).
        
        Creates PublicKeyCredentialCreationOptions with:
        - Relying Party info (our domain)
        - User info (id, name, display name)
        - Challenge (random bytes)
        - Authenticator selection (platform + cross-platform)
        """
        # Check if username is taken
        existing = await self.db.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            raise ValueError(f"Username '{username}' is already taken")

        # Check if email is taken
        existing_email = await self.db.execute(select(User).where(User.email == email))
        if existing_email.scalar_one_or_none():
            raise ValueError(f"Email '{email}' is already registered")

        user_id = uuid.uuid4()

        options = generate_registration_options(
            rp_id=settings.webauthn_rp_id,
            rp_name=settings.webauthn_rp_name,
            user_id=str(user_id).encode(),
            user_name=username,
            user_display_name=display_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )

        # Store challenge for verification
        challenge_entry = WebAuthnChallenge(
            challenge=base64.b64encode(options.challenge).decode(),
            user_id=user_id,
            challenge_type="registration",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        self.db.add(challenge_entry)
        await self.db.flush()

        # Store pending user data in challenge metadata
        import json
        options_json = json.loads(options_to_json(options))

        return {
            "options": options_json,
            "challenge_id": str(challenge_entry.id),
            "_pending_user": {
                "user_id": str(user_id),
                "username": username,
                "display_name": display_name,
                "email": email,
            },
        }

    async def complete_registration(
        self, credential: dict, challenge_id: str,
        username: str = "", display_name: str = "", email: str = "",
    ) -> User:
        """Verify WebAuthn attestation and create user + passkey.
        
        Validates the authenticator's response against our challenge,
        extracts the public key, and stores the credential.
        """
        # Retrieve challenge
        challenge_entry = await self.db.get(WebAuthnChallenge, uuid.UUID(challenge_id))
        if not challenge_entry or challenge_entry.expires_at < datetime.now(timezone.utc):
            raise ValueError("Challenge expired or not found")

        expected_challenge = base64.b64decode(challenge_entry.challenge)

        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origin,
        )

        # Create user
        user = User(
            id=challenge_entry.user_id,
            username=username or f"user_{challenge_entry.user_id}",
            display_name=display_name or "New User",
            email=email or "",
        )
        self.db.add(user)

        # Store passkey credential
        passkey = Passkey(
            user_id=user.id,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            aaguid=str(verification.aaguid) if verification.aaguid else None,
        )
        self.db.add(passkey)

        # Initialize gamification state
        gamification = UserGamification(user_id=user.id)
        self.db.add(gamification)

        # Initialize portfolio
        portfolio = Portfolio(user_id=user.id)
        self.db.add(portfolio)

        # Clean up challenge
        await self.db.delete(challenge_entry)
        await self.db.flush()

        logger.info("User registered via WebAuthn", user_id=str(user.id), username=user.username)
        return user

    async def begin_authentication(self, username: str) -> dict[str, Any]:
        """Generate WebAuthn authentication options.
        
        Looks up user's registered credentials and generates a challenge
        with allowCredentials list.
        """
        # Find user
        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        # Get user's passkeys
        passkeys_result = await self.db.execute(
            select(Passkey).where(Passkey.user_id == user.id)
        )
        passkeys = passkeys_result.scalars().all()
        if not passkeys:
            raise ValueError("No passkeys registered for this user")

        allow_credentials = [
            PublicKeyCredentialDescriptor(id=pk.credential_id)
            for pk in passkeys
        ]

        options = generate_authentication_options(
            rp_id=settings.webauthn_rp_id,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        # Store challenge
        challenge_entry = WebAuthnChallenge(
            challenge=base64.b64encode(options.challenge).decode(),
            user_id=user.id,
            challenge_type="authentication",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        self.db.add(challenge_entry)
        await self.db.flush()

        return {
            "options": json.loads(options_to_json(options)),
            "challenge_id": str(challenge_entry.id),
        }

    async def complete_authentication(self, credential: dict, challenge_id: str) -> User:
        """Verify WebAuthn assertion and authenticate user.
        
        Validates the authenticator's signature against the stored public key.
        """
        challenge_entry = await self.db.get(WebAuthnChallenge, uuid.UUID(challenge_id))
        if not challenge_entry or challenge_entry.expires_at < datetime.now(timezone.utc):
            raise ValueError("Challenge expired or not found")

        expected_challenge = base64.b64decode(challenge_entry.challenge)

        # Find the passkey by credential ID
        credential_id_bytes = base64.urlsafe_b64decode(
            credential.get("id", "") + "=="  # padding
        )
        result = await self.db.execute(
            select(Passkey).where(Passkey.credential_id == credential_id_bytes)
        )
        passkey = result.scalar_one_or_none()
        if not passkey:
            raise ValueError("Credential not recognized")

        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origin,
            credential_public_key=passkey.public_key,
            credential_current_sign_count=passkey.sign_count,
        )

        # Update sign count
        passkey.sign_count = verification.new_sign_count
        passkey.last_used_at = datetime.now(timezone.utc)

        # Get user
        user = await self.db.get(User, passkey.user_id)

        # Clean up challenge
        await self.db.delete(challenge_entry)
        await self.db.flush()

        logger.info("User authenticated via WebAuthn", user_id=str(user.id))
        return user

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await self.db.get(User, uuid.UUID(user_id))
