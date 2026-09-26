import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    """Return the user when credentials are valid, otherwise None."""
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized = email.strip().lower()
    return db.execute(select(User).where(func.lower(User.email) == normalized)).scalar_one_or_none()


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


def create_user(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
    role: UserRole,
) -> User:
    email = email.strip().lower()
    if get_user_by_email(db, email) is not None:
        raise ConflictError("A user with this email already exists")
    user = User(
        name=name.strip(),
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user: User,
    *,
    name: str | None = None,
    role: UserRole | None = None,
    password: str | None = None,
) -> User:
    if name is not None:
        user.name = name.strip()
    if role is not None:
        user.role = role
    if password is not None:
        user.password_hash = hash_password(password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, *, page: int, page_size: int) -> tuple[list[User], int]:
    total = db.execute(select(func.count()).select_from(User)).scalar_one()
    users = (
        db.execute(
            select(User)
            .order_by(User.created_at, User.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(users), total


def issue_token(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id, user.role.value),
        "token_type": "bearer",
    }
