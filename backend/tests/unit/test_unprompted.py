"""
Unit tests — unprompted completion attribution (Habit Engine §6.1).

"Delivery time rather than send time is the whole subtlety here."
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.occurrences.service import compute_unprompted


UTC = timezone.utc


class TestUnpromptedAttribution:
    def test_no_prompt_sent_is_always_unprompted(self):
        completed = datetime(2025, 1, 1, 8, 15, tzinfo=UTC)
        assert compute_unprompted(None, None, completed) is True

    def test_completion_before_delivery_is_unprompted(self):
        """
        Classic case: prompt sent at 07:00, delivered at 09:40 (phone offline),
        user completed at 08:15 → unprompted.
        """
        sent = datetime(2025, 1, 1, 7, 0, tzinfo=UTC)
        delivered = datetime(2025, 1, 1, 9, 40, tzinfo=UTC)
        completed = datetime(2025, 1, 1, 8, 15, tzinfo=UTC)
        assert compute_unprompted(sent, delivered, completed) is True

    def test_completion_after_delivery_is_prompted(self):
        sent = datetime(2025, 1, 1, 7, 0, tzinfo=UTC)
        delivered = datetime(2025, 1, 1, 7, 1, tzinfo=UTC)
        completed = datetime(2025, 1, 1, 7, 30, tzinfo=UTC)
        assert compute_unprompted(sent, delivered, completed) is False

    def test_no_delivery_receipt_falls_back_to_send_time(self):
        """When delivery receipt is unavailable, send time is used as fallback."""
        sent = datetime(2025, 1, 1, 7, 0, tzinfo=UTC)
        # Completion at 06:58 — before the send, so unprompted
        completed = datetime(2025, 1, 1, 6, 58, tzinfo=UTC)
        assert compute_unprompted(sent, None, completed) is True

    def test_exactly_at_delivery_boundary(self):
        """Completion exactly at delivery time — counts as prompted (not before)."""
        sent = datetime(2025, 1, 1, 7, 0, tzinfo=UTC)
        delivered = datetime(2025, 1, 1, 7, 0, tzinfo=UTC)
        completed = datetime(2025, 1, 1, 7, 0, tzinfo=UTC)
        # completed is not BEFORE delivery
        assert compute_unprompted(sent, delivered, completed) is False

    def test_probe_day_with_sent_time_is_handled_correctly(self):
        """
        On probe days, prompt_policy=probe means prompt_sent_at is None.
        Completion on a probe day is always unprompted.
        """
        completed = datetime(2025, 1, 1, 7, 30, tzinfo=UTC)
        assert compute_unprompted(None, None, completed) is True
