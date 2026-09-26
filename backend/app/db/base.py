from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

# JSON with PostgreSQL JSONB variant. Falls back to generic JSON on other
# dialects (e.g. SQLite for tests).
JSONType = JSON().with_variant(JSONB(), "postgresql")


def enum_values(enum_cls) -> list[str]:
    """Persist Python enum `.value` strings (e.g. 'open') instead of member names.

    Keeps DB values in sync with the CHECK constraints defined in migrations.
    """
    return [member.value for member in enum_cls]


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
