"""Filtering and pagination behaviour of AuditService.list_audit_logs.

The date-range bug this file guards against: `count_stmt` used to be built
independently of the item query and silently omitted the date filters, so the
returned `total`/`total_pages` counted the whole table while `items` was
filtered. Clients then saw phantom pages.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models import AuditLog
from app.services.audit_service import AuditService

# A fixed reference point so the fixtures never depend on the wall clock.
BASE = datetime(2026, 3, 1, 12, 0, 0)
DAY = timedelta(days=1)


def _log(db: Session, *, days: int, action: str = "evidence.upload",
         entity_type: str = "evidence", user_id=None) -> AuditLog:
    """Insert an audit log at BASE + `days` days."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        timestamp=BASE + days * DAY,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@pytest.fixture()
def five_days(db_session: Session) -> list[AuditLog]:
    """One log per day, five consecutive days starting at BASE."""
    return [_log(db_session, days=i) for i in range(5)]


# --- date_from / date_to reach the count ---------------------------------


def test_date_from_alone_narrows_total(db_session: Session, five_days):
    """date_from must constrain `total`, not just the returned page."""
    result = AuditService.list_audit_logs(db_session, date_from=BASE + 3 * DAY)

    assert len(result["items"]) == 2
    assert result["total"] == 2, (
        f"total was {result['total']} but only 2 logs are on/after the cutoff; "
        "the count query is not applying date_from"
    )


def test_date_to_alone_narrows_total(db_session: Session, five_days):
    result = AuditService.list_audit_logs(db_session, date_to=BASE + DAY)

    assert len(result["items"]) == 2
    assert result["total"] == 2


def test_date_range_narrows_total(db_session: Session, five_days):
    result = AuditService.list_audit_logs(
        db_session, date_from=BASE + DAY, date_to=BASE + 2 * DAY
    )

    assert len(result["items"]) == 2
    assert result["total"] == 2


def test_total_pages_reflects_the_date_range(db_session: Session, five_days):
    """total_pages is derived from total, so it inherits the same defect."""
    result = AuditService.list_audit_logs(
        db_session, date_from=BASE + 3 * DAY, page_size=1
    )

    assert result["total"] == 2
    assert result["total_pages"] == 2, "a date-filtered query must not promise 5 pages"


# --- date range + pagination together ------------------------------------


def test_date_filtered_pagination_has_no_empty_pages(db_session: Session, five_days):
    """Every page promised by total_pages must actually contain items.

    This is the user-visible symptom: with the unfiltered count, page 3 of a
    2-page result set came back empty.
    """
    total_pages = AuditService.list_audit_logs(
        db_session, date_from=BASE + 3 * DAY, page_size=1
    )["total_pages"]

    for page in range(1, total_pages + 1):
        result = AuditService.list_audit_logs(
            db_session, page=page, page_size=1, date_from=BASE + 3 * DAY
        )
        assert result["items"], f"page {page} of {total_pages} was empty"


def test_date_filtered_page_size_total_is_consistent(db_session: Session, five_days):
    """Walk the whole filtered result set and count what actually arrives."""
    collected: list[str] = []
    page = 1
    while True:
        result = AuditService.list_audit_logs(
            db_session, page=page, page_size=2, date_from=BASE + 2 * DAY
        )
        if not result["items"]:
            break
        collected.extend(item["id"] for item in result["items"])
        page += 1

    assert len(collected) == 3  # days 2, 3, 4
    assert len(set(collected)) == 3, "a log was returned on two pages"


# --- date filters combine with the other filters -------------------------


def test_date_filter_combines_with_action(db_session: Session):
    _log(db_session, days=0, action="evidence.upload")
    _log(db_session, days=5, action="evidence.upload")
    _log(db_session, days=5, action="case.create")

    result = AuditService.list_audit_logs(
        db_session, action="evidence.upload", date_from=BASE + DAY
    )

    assert result["total"] == 1
    assert result["items"][0]["action"] == "evidence.upload"


def test_date_filter_combines_with_entity_type(db_session: Session):
    _log(db_session, days=0, entity_type="evidence")
    _log(db_session, days=5, entity_type="evidence")
    _log(db_session, days=5, entity_type="case")

    result = AuditService.list_audit_logs(
        db_session, entity_type="evidence", date_from=BASE + DAY
    )

    assert result["total"] == 1
    assert result["items"][0]["entity_type"] == "evidence"


def test_date_filter_combines_with_user_id(db_session: Session):
    from app.core.enums import UserRole
    from app.core.security import hash_password
    from app.models import User

    alice = User(name="A", email="a@t.local", password_hash=hash_password("Pw123456!"),
                 role=UserRole.VIEWER)
    bob = User(name="B", email="b@t.local", password_hash=hash_password("Pw123456!"),
               role=UserRole.VIEWER)
    db_session.add_all([alice, bob])
    db_session.commit()

    _log(db_session, days=0, user_id=alice.id)
    _log(db_session, days=0, user_id=bob.id)
    _log(db_session, days=5, user_id=alice.id)

    result = AuditService.list_audit_logs(
        db_session, user_id=alice.id, date_from=BASE + DAY
    )

    assert result["total"] == 1
    assert result["items"][0]["user_email"] == "a@t.local"


def test_all_three_filters_together(db_session: Session, five_days):
    result = AuditService.list_audit_logs(
        db_session,
        action="evidence.upload",
        entity_type="evidence",
        date_from=BASE + 2 * DAY,
        date_to=BASE + 3 * DAY,
    )

    assert result["total"] == 2
    assert len(result["items"]) == 2


# --- no filters is unchanged ---------------------------------------------


def test_unfiltered_total_counts_everything(db_session: Session, five_days):
    result = AuditService.list_audit_logs(db_session, page_size=100)

    assert result["total"] == 5
    assert len(result["items"]) == 5
    assert result["total_pages"] == 1


def test_empty_result_reports_zero_total_pages(db_session: Session, five_days):
    result = AuditService.list_audit_logs(db_session, date_from=BASE + 30 * DAY)

    assert result["items"] == []
    assert result["total"] == 0
    assert result["total_pages"] == 0


def test_date_range_excluding_everything_is_empty(db_session: Session, five_days):
    result = AuditService.list_audit_logs(
        db_session, date_from=BASE + 10 * DAY, date_to=BASE + 20 * DAY
    )

    assert result["total"] == 0
    assert result["items"] == []
