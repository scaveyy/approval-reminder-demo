# Approvals and reminders without silent state changes

This Python demo tracks an invented office request. It shows how a decision changes the request state and when a reminder should be proposed. The people, dates, and request are fictional. There is no employer or client data and no connection to an email or workflow service.

## Try it

Use Python 3.10 or later. No packages, accounts, or network calls are needed.

```sh
python3 -m unittest discover -s tests -v
python3 approval.py
```

The example checks an overdue pending request, then applies an approval. A reminder is due before the decision and disappears after it. No reminder is sent by this code.

## What the code checks

1. Require a timezone on every time value. The due time must follow creation.
2. Accept only `approve` or `reject` while a request is pending. Only its assigned approver can decide.
3. Require the expected revision before changing state. A stale decision stops instead of overwriting a newer state.
4. Treat an exact event replay as already handled. Reusing the same event ID with different content stops with an error.
5. Give each due reminder a stable key. A caller can use that key to avoid sending the same reminder twice. Closed requests never get a new reminder.

The 14 tests cover those rules, including self approval, stale revisions, changed event content, missing timezones, and reminder suppression. GitHub Actions runs the tests on pushes and pull requests.

## What this does not prove

This is a local state machine, not a deployed approval service. Names and roles in the example are supplied as input; there is no authentication. The code proposes reminders but does not send them or save the sent-key ledger. A real system would need durable storage, access checks, concurrency control at the database, delivery receipts, and a recheck immediately before sending. This example does not claim those controls or any result from another project.
