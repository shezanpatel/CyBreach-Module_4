from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.repositories.wallet_repository import get_wallet_audit_entries


# ============================================================
# HELPERS
# ============================================================


def make_query_mock():
    """
    Build a chainable SQLAlchemy-style query mock.

    Every query operation returns the same mock so the repository
    function can build filters, ordering, and pagination normally.
    """
    query = MagicMock()

    query.filter.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query

    query.count.return_value = 4
    query.all.return_value = ["entry-1", "entry-2"]

    return query


# ============================================================
# BASIC QUERY
# ============================================================


def test_audit_query_returns_entries_and_total():
    db = MagicMock()
    query = make_query_mock()

    db.query.return_value = query

    entries, total = get_wallet_audit_entries(
        db=db,
        user_id="audit-user",
    )

    assert entries == ["entry-1", "entry-2"]
    assert total == 4

    db.query.assert_called_once()

    query.count.assert_called_once()
    query.offset.assert_called_once_with(0)
    query.limit.assert_called_once_with(100)
    query.all.assert_called_once()


# ============================================================
# PAGINATION
# ============================================================


def test_audit_query_applies_limit_and_offset():
    db = MagicMock()
    query = make_query_mock()

    db.query.return_value = query

    get_wallet_audit_entries(
        db=db,
        user_id="audit-user",
        limit=25,
        offset=50,
    )

    query.offset.assert_called_once_with(50)
    query.limit.assert_called_once_with(25)


@pytest.mark.parametrize(
    ("limit", "offset", "expected_message"),
    [
        (0, 0, "limit must be greater than zero"),
        (1001, 0, "limit must not exceed 1000"),
        (100, -1, "offset must not be negative"),
    ],
)
def test_audit_query_rejects_invalid_pagination(
    limit,
    offset,
    expected_message,
):
    db = MagicMock()

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        get_wallet_audit_entries(
            db=db,
            user_id="audit-user",
            limit=limit,
            offset=offset,
        )

    db.query.assert_not_called()


# ============================================================
# ENTRY TYPE
# ============================================================


def test_audit_query_accepts_debit_entry_type():
    db = MagicMock()
    query = make_query_mock()

    db.query.return_value = query

    get_wallet_audit_entries(
        db=db,
        user_id="audit-user",
        entry_type="DEBIT",
    )

    assert query.filter.call_count == 2


def test_audit_query_normalizes_credit_entry_type():
    db = MagicMock()
    query = make_query_mock()

    db.query.return_value = query

    get_wallet_audit_entries(
        db=db,
        user_id="audit-user",
        entry_type="credit",
    )

    assert query.filter.call_count == 2


def test_audit_query_rejects_invalid_entry_type():
    db = MagicMock()
    query = make_query_mock()

    db.query.return_value = query

    with pytest.raises(
        ValueError,
        match="entry_type must be DEBIT or CREDIT",
    ):
        get_wallet_audit_entries(
            db=db,
            user_id="audit-user",
            entry_type="INVALID",
        )


# ============================================================
# MODULE SOURCE
# ============================================================


def test_audit_query_applies_module_source_filter():
    db = MagicMock()
    query = make_query_mock()

    db.query.return_value = query

    get_wallet_audit_entries(
        db=db,
        user_id="audit-user",
        module_source="mod4",
    )

    assert query.filter.call_count == 2


# ============================================================
# DATE RANGE
# ============================================================


def test_audit_query_applies_date_range():
    db = MagicMock()
    query = make_query_mock()

    db.query.return_value = query

    date_from = datetime(
        2026,
        9,
        1,
        tzinfo=timezone.utc,
    )

    date_to = datetime(
        2026,
        9,
        30,
        23,
        59,
        59,
        tzinfo=timezone.utc,
    )

    get_wallet_audit_entries(
        db=db,
        user_id="audit-user",
        date_from=date_from,
        date_to=date_to,
    )

    # user_id + date_from + date_to
    assert query.filter.call_count == 3


def test_audit_query_rejects_reversed_date_range():
    db = MagicMock()

    date_from = datetime(
        2026,
        9,
        30,
        tzinfo=timezone.utc,
    )

    date_to = datetime(
        2026,
        9,
        1,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ValueError,
        match=(
            "date_from must be earlier than or equal to date_to"
        ),
    ):
        get_wallet_audit_entries(
            db=db,
            user_id="audit-user",
            date_from=date_from,
            date_to=date_to,
        )

    db.query.assert_not_called()


# ============================================================
# COMBINED FILTERS
# ============================================================


def test_audit_query_combines_all_filters():
    db = MagicMock()
    query = make_query_mock()

    db.query.return_value = query

    date_from = datetime(
        2026,
        9,
        1,
        tzinfo=timezone.utc,
    )

    date_to = datetime(
        2026,
        9,
        30,
        tzinfo=timezone.utc,
    )

    entries, total = get_wallet_audit_entries(
        db=db,
        user_id="audit-user",
        date_from=date_from,
        date_to=date_to,
        entry_type="credit",
        module_source="mod4",
        limit=20,
        offset=40,
    )

    assert entries == ["entry-1", "entry-2"]
    assert total == 4

    # user_id
    # date_from
    # date_to
    # entry_type
    # module_source
    assert query.filter.call_count == 5

    query.offset.assert_called_once_with(40)
    query.limit.assert_called_once_with(20)
