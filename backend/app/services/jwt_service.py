import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt


class JWTService:
    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str | None = None,
        expiration_minutes: int | None = None,
    ) -> None:
        self.secret_key = ( secret_key
                            if secret_key is not None
                            else os.getenv("JWT_SECRET_KEY")
        )
        self.algorithm = algorithm or os.getenv("JWT_ALGORITHM", "HS256")

        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY is not configured.")

        if self.algorithm != "HS256":
            raise ValueError("Only HS256 is supported.")

        self.expiration_minutes = (
            expiration_minutes
            if expiration_minutes is not None
            else int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
        )

        if self.expiration_minutes <= 0:
            raise ValueError("JWT expiration must be greater than zero.")

    def create_access_token(self, user_id: UUID) -> str:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.expiration_minutes)

        payload = {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": expires_at,
        }

        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def decode_access_token(self, token: str) -> dict:
        payload = jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
            options={
                "require": ["sub", "type", "iat", "exp"]
            },
        )

        if payload.get("type") != "access":
            raise jwt.InvalidTokenError(
                "Invalid token type."
            )

        subject = payload.get("sub")

        if not isinstance(subject, str):
            raise jwt.InvalidTokenError("Invalid token subject.")

        try:
            UUID(subject)
        except ValueError:
            raise jwt.InvalidTokenError(
                "Invalid token subject."
            ) from None

        return payload
