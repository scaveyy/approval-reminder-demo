import dataclasses
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from approval import WorkflowError, apply_event, due_reminder, load_case  # noqa: E402


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.request, self.event, self.check_at = load_case()

    def test_due_reminder_has_stable_key(self):
        reminder = due_reminder(self.request, self.check_at, set())
        self.assertEqual(reminder.key, "REQ-101:0:due")
        self.assertEqual(reminder.recipient, "morgan")

    def test_no_reminder_before_due_time(self):
        self.assertIsNone(due_reminder(self.request, "2026-01-12T08:59:59+00:00", set()))

    def test_sent_key_suppresses_repeat_reminder(self):
        self.assertIsNone(due_reminder(self.request, self.check_at, {"REQ-101:0:due"}))

    def test_approval_closes_request_and_stops_reminder(self):
        decided = apply_event(self.request, self.event)
        self.assertEqual((decided.status, decided.revision), ("approved", 1))
        self.assertIsNone(due_reminder(decided, self.check_at, set()))

    def test_rejection_also_stops_reminder(self):
        rejected = apply_event(self.request, dataclasses.replace(self.event, kind="reject"))
        self.assertEqual(rejected.status, "rejected")
        self.assertIsNone(due_reminder(rejected, self.check_at, set()))

    def test_exact_event_replay_is_idempotent(self):
        decided = apply_event(self.request, self.event)
        self.assertEqual(apply_event(decided, self.event), decided)

    def test_reused_event_id_with_other_content_is_rejected(self):
        decided = apply_event(self.request, self.event)
        changed = dataclasses.replace(self.event, kind="reject")
        with self.assertRaisesRegex(WorkflowError, "reused"):
            apply_event(decided, changed)

    def test_stale_revision_is_rejected(self):
        stale = dataclasses.replace(self.event, expected_revision=1)
        with self.assertRaisesRegex(WorkflowError, "stale"):
            apply_event(self.request, stale)

    def test_requester_cannot_approve(self):
        wrong_actor = dataclasses.replace(self.event, actor=self.request.requester)
        with self.assertRaisesRegex(WorkflowError, "assigned approver"):
            apply_event(self.request, wrong_actor)

    def test_self_approval_configuration_is_rejected(self):
        bad = dataclasses.replace(self.request, approver=self.request.requester)
        with self.assertRaisesRegex(WorkflowError, "invalid request identity"):
            due_reminder(bad, self.check_at, set())

    def test_naive_timestamps_are_rejected(self):
        with self.assertRaisesRegex(WorkflowError, "timezone"):
            due_reminder(self.request, "2026-01-12T09:30:00", set())

    def test_decision_before_request_is_rejected(self):
        early = dataclasses.replace(self.event, at="2026-01-09T10:00:00+00:00")
        with self.assertRaisesRegex(WorkflowError, "predates"):
            apply_event(self.request, early)

    def test_wrong_request_id_is_rejected(self):
        wrong = dataclasses.replace(self.event, request_id="REQ-999")
        with self.assertRaisesRegex(WorkflowError, "event identity"):
            apply_event(self.request, wrong)

    def test_inconsistent_state_is_rejected(self):
        bad = dataclasses.replace(self.request, status="approved")
        with self.assertRaisesRegex(WorkflowError, "inconsistent"):
            due_reminder(bad, self.check_at, set())


if __name__ == "__main__":
    unittest.main()
