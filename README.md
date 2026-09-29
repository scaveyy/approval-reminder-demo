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

## Scope

A local state machine with fictional data. It proposes reminders but does not send them, and it has no login or database.

## How this maps to a production build

I build approval and reminder flows in production with Power Apps, SharePoint and Power Automate. There, the state lives in SharePoint or Dataverse and Power Automate sends the reminders. This repo shows the rules those flows have to respect (stale decisions, replays, no duplicate reminders) in a form anyone can run.
