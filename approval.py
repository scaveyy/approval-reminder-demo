"""Local approval and reminder state machine over invented requests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path


EXAMPLE = Path(__file__).parent / "examples" / "case.json"
ID_PATTERN = re.compile(r"[A-Z0-9-]{3,40}\Z")


class WorkflowError(ValueError):
    """The requested transition or reminder is unsafe."""


def aware_time(value: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise WorkflowError("invalid timestamp") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise WorkflowError("timestamp needs a timezone")
    return timestamp


@dataclass(frozen=True)
class Request:
    request_id: str
    requester: str
    approver: str
    created_at: str
    due_at: str
    status: str = "pending"
    revision: int = 0
    seen_events: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Event:
    event_id: str
    request_id: str
    kind: str
    actor: str
    expected_revision: int
    at: str

    @property
    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Reminder:
    key: str
    request_id: str
    due_at: str
    recipient: str


def validate_request(request: Request) -> None:
    if (not ID_PATTERN.fullmatch(request.request_id)
            or not request.requester.strip() or not request.approver.strip()
            or request.requester == request.approver):
        raise WorkflowError("invalid request identity")
    if request.status not in {"pending", "approved", "rejected"}:
        raise WorkflowError("invalid request status")
    if type(request.revision) is not int or request.revision < 0:
        raise WorkflowError("invalid request revision")
    if (request.status == "pending" and (request.revision != 0 or request.seen_events)
            or request.status != "pending" and
            (request.revision != 1 or len(request.seen_events) != 1)):
        raise WorkflowError("inconsistent request state")
    for event_id, fingerprint in request.seen_events:
        if not ID_PATTERN.fullmatch(event_id) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise WorkflowError("invalid event history")
    if aware_time(request.due_at) <= aware_time(request.created_at):
        raise WorkflowError("due time must follow creation")


def apply_event(request: Request, event: Event) -> Request:
    """Apply one decision. Exact event replays return the same state."""
    validate_request(request)
    if not ID_PATTERN.fullmatch(event.event_id) or event.request_id != request.request_id:
        raise WorkflowError("invalid event identity")
    prior = dict(request.seen_events)
    if event.event_id in prior:
        if prior[event.event_id] != event.fingerprint:
            raise WorkflowError("event ID reused with different content")
        return request
    if type(event.expected_revision) is not int or event.expected_revision != request.revision:
        raise WorkflowError("stale request revision")
    if request.status != "pending" or event.kind not in {"approve", "reject"}:
        raise WorkflowError("invalid state transition")
    if event.actor != request.approver:
        raise WorkflowError("only the assigned approver may decide")
    if aware_time(event.at) < aware_time(request.created_at):
        raise WorkflowError("decision predates request")
    return replace(
        request,
        status="approved" if event.kind == "approve" else "rejected",
        revision=request.revision + 1,
        seen_events=(*request.seen_events, (event.event_id, event.fingerprint)),
    )


def due_reminder(
    request: Request, now: str, sent_keys: set[str] | frozenset[str]
) -> Reminder | None:
    """Propose a reminder; sending and saving the dedupe key are external steps."""
    validate_request(request)
    current_time = aware_time(now)
    key = f"{request.request_id}:{request.revision}:due"
    if (request.status != "pending" or current_time < aware_time(request.due_at)
            or key in sent_keys):
        return None
    return Reminder(key, request.request_id, request.due_at, request.approver)


def load_case(path: Path = EXAMPLE) -> tuple[Request, Event, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"request", "decision", "check_at"}:
        raise WorkflowError("case needs request, decision, and check_at")
    if not isinstance(data["request"], dict) or not isinstance(data["decision"], dict):
        raise WorkflowError("invalid case fields")
    required_request = {"request_id", "requester", "approver", "created_at", "due_at"}
    required_event = {"event_id", "request_id", "kind", "actor", "expected_revision", "at"}
    if set(data["request"]) != required_request or set(data["decision"]) != required_event:
        raise WorkflowError("invalid case fields")
    request = Request(**data["request"])
    event = Event(**data["decision"])
    validate_request(request)
    aware_time(data["check_at"])
    return request, event, data["check_at"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=EXAMPLE)
    args = parser.parse_args()
    request, event, check_at = load_case(args.case)
    reminder = due_reminder(request, check_at, set())
    decided = apply_event(request, event)
    after_decision = due_reminder(decided, check_at, set())
    print(json.dumps({
        "reminder_before_decision": asdict(reminder) if reminder else None,
        "state_after_decision": {"status": decided.status, "revision": decided.revision},
        "reminder_after_decision": asdict(after_decision) if after_decision else None,
    }, indent=2))


if __name__ == "__main__":
    main()
