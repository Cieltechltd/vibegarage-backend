"""Helpers for checking listener access to groups of tracks."""

from collections.abc import Iterable
from typing import Any

from sqlalchemy.orm import Session

from app.models.purchase import Purchase


def get_owned_track_ids(
    db: Session,
    user_id: str,
    track_ids: Iterable[Any],
) -> set[Any]:
    """Return the purchased track IDs from one query for a track collection."""
    unique_track_ids = set(track_ids)
    if not unique_track_ids:
        return set()

    rows = (
        db.query(Purchase.track_id)
        .filter(
            Purchase.user_id == user_id,
            Purchase.track_id.in_(unique_track_ids),
        )
        .all()
    )
    return {row[0] for row in rows}
