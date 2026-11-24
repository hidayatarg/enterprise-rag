import pytest
from app.services.password_service import PasswordService

@pytest.fixture
def service() -> PasswordService:
    return PasswordService()


def test_hash_password_returns_argon2_hash(
    service: PasswordService,
) -> None:
    password = "MySecurePassword123!"

    password_hash = service.hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2id$")


def test_same_password_generates_different_hashes(
    service: PasswordService,
) -> None:
    password = "MySecurePassword123!"

    first_hash = service.hash_password(password)
    second_hash = service.hash_password(password)

    assert first_hash != second_hash


def test_verify_password_success(
    service: PasswordService,
) -> None:
    password = "MySecurePassword123!"
    password_hash = service.hash_password(password)

    result = service.verify_password(
        password,
        password_hash,
    )

    assert result is True


def test_verify_password_failure(
    service: PasswordService,
) -> None:
    password_hash = service.hash_password(
        "CorrectPassword123!"
    )

    result = service.verify_password(
        "WrongPassword123!",
        password_hash,
    )

    assert result is False


def test_verify_password_with_invalid_hash(
    service: PasswordService,
) -> None:
    result = service.verify_password(
        "Password123!",
        "invalid-hash",
    )

    assert result is False


def test_empty_password_is_rejected(
    service: PasswordService,
) -> None:
    with pytest.raises(
        ValueError,
        match="Password cannot be empty",
    ):
        service.hash_password("")


def test_current_hash_does_not_require_rehash(
    service: PasswordService,
) -> None:
    password_hash = service.hash_password(
        "MySecurePassword123!"
    )

    assert service.needs_rehash(password_hash) is False
