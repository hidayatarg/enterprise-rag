
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import User
from app.schemas.auth_schemas import UserRegisterRequest
from app.services.password_service import password_service


class UsernameAlreadyExistsError(Exception):
    pass

class InvalidCredentialsError(Exception):
    pass


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_username(self, username: str) -> User | None:
        statement = select(User).where(
            User.username == username.strip().lower()
        )

        return self.db.scalar(statement)

    def register_user(self, request: UserRegisterRequest) -> User:
        existing_user = self.get_by_username(request.username)

        if existing_user is not None:
            raise UsernameAlreadyExistsError(
                "Username is already registered."
            )

        user = User(
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name,
            company=request.company,
            job_title=request.job_title,
            password_hash=password_service.hash_password(
                request.password
            ),
        )

        self.db.add(user)

        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()

            # A unique constraint also protects against concurrent
            # registrations using the same username.
            raise UsernameAlreadyExistsError(
                "Username is already registered."
            ) from None

        self.db.refresh(user)

        return user


    def authenticate_user(
        self,
        username: str,
        password: str,
    ) -> User:
        user = self.get_by_username(username)

        if user is None:
            raise InvalidCredentialsError("Invalid username or password.")

        if not password_service.verify_password(
            password,
            user.password_hash,
        ):
            raise InvalidCredentialsError("Invalid username or password.")

        if not user.is_active:
            raise InvalidCredentialsError("Invalid username or password.")

        return user
