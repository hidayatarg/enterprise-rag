from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)


class PasswordService:
    """
    Handles password hashing and verification using Argon2id.

    Plain-text passwords must never be persisted in the database.
    """
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def hash_password(self, password: str) -> str:
        """
        Generate a salted Argon2id password hash.
        """
        if not password:
            raise ValueError("Password cannot be empty.")

        return self._hasher.hash(password)

    def verify_password(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        """
        Verify a password against a stored Argon2 hash.

        Returns False when the password is incorrect or the
        stored hash is invalid.
        """
        try:
            return self._hasher.verify(password_hash, password)
        except (
            VerifyMismatchError,
            InvalidHashError,
            VerificationError,
        ):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        """
        Check whether an existing hash should be upgraded
        to the current Argon2 parameters.
        """
        return self._hasher.check_needs_rehash(password_hash)


password_service = PasswordService()