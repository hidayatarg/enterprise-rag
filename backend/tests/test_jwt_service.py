from uuid import uuid4

import jwt
import pytest

from app.services.jwt_service import JWTService


@pytest.fixture
def service() -> JWTService:
    return JWTService(
        secret_key="test-secret-key-for-unit-tests-only",
        algorithm="HS256",
        expiration_minutes=15,
    )


def test_create_and_decode_access_token(
    service: JWTService,
) -> None:
    user_id = uuid4()

    token = service.create_access_token(user_id)

    payload = service.decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert payload["exp"] > payload["iat"]


def test_rejects_invalid_signature(
    service: JWTService,
) -> None:
    token = JWTService(
        secret_key="another-test-secret-key",
    ).create_access_token(uuid4())

    with pytest.raises(jwt.InvalidSignatureError):
        service.decode_access_token(token)


def test_rejects_expired_token(
    service: JWTService,
) -> None:
    import time

    payload = {
        "sub": str(uuid4()),
        "type": "access",
        "iat": int(time.time()) - 3600,
        "exp": int(time.time()) - 10,
    }

    token = jwt.encode(
        payload,
        service.secret_key,
        algorithm="HS256",
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        service.decode_access_token(token)


def test_rejects_wrong_token_type(
    service: JWTService,
) -> None:
    import time

    payload = {
        "sub": str(uuid4()),
        "type": "refresh",
        "iat": int(time.time()),
        "exp": int(time.time()) + 900,
    }

    token = jwt.encode(
        payload,
        service.secret_key,
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidTokenError):
        service.decode_access_token(token)


def test_rejects_missing_secret() -> None:
    with pytest.raises(
        ValueError,
        match="JWT_SECRET_KEY is not configured",
    ):
        JWTService(
            secret_key="",
        )