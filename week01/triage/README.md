# Week 1: Ticket Triage, your first AI-backed function

**The brief in one sentence:** write a small, trustworthy function that reads a customer support ticket and returns a validated, structured triage, using the Gemini API.

The tickets belong to **Neemtree Billing, a fictional invoicing app**. The data is synthetic. Nobody real is in it.

## What `triage()` does

`triage(ticket_text, client) -> Triage` where a `Triage` has:

| Field | Values |
|---|---|
| `category` | billing, bug, how_to, account_access, feature_request, other |
| `priority` | P1, P2, P3, P4 |
| `summary` | at most 25 words |
| `needs_human` | true or false |
| `reason` | one sentence: why this category and priority |

It asks the model for structured output, **validates** the reply with Pydantic, **retries once** (telling the model what was wrong) and otherwise raises `TriageError`. It never returns unvalidated data. It writes a **trace** line for every attempt to `traces/YYYY-MM-DD.jsonl`.

## What is provided and what is yours

| File | Status |
|---|---|
| `models.py`, `llm.py`, `run.py`, `data/` | Provided. Read them. You will debug through them |
| `triage.py` | The system instruction is provided. The validation, retry and trace logic are **your TODOs** |
| `tests/test_triage.py` | Four tests. They fail until your TODOs are done |
| `EXPLAIN.md`, `AI_LOG.md` | Yours to fill in |

## Your steps

0. **Branch first.** Before you change anything: `git switch -c week01`. Commit often as you go.
1. **Make the four tests pass.** From the repo root: `python -m pytest week01/triage/tests`. They use a `FakeClient`, so no key or network is needed. Read each failure before you change anything.
2. **Run it for real** on the 12 tickets: `python week01/triage/run.py --eval`. Write down both accuracies. Want to see the table before you have a key? Add `--fake` (a crude keyword guesser, not an AI).
3. **Variation experiment.** Run one ticket five times at temperature 1.0, and five times at 0:
   `python week01/triage/run.py --ticket 4 --repeat 5 --temperature 1.0`
   Record what changed and what did not.
4. **Context experiment.** Change **one** thing in `SYSTEM_INSTRUCTION` (clearer definitions, or two labelled examples). Re-run `--eval`. Record before and after.
5. **Fill in `EXPLAIN.md`.** Answer first. Walk through every line you did not type yourself.
6. **Fill in `AI_LOG.md`.** What you asked your assistant, what you kept, what you rejected and why.
7. **Open a pull request.** `git add .`, `git commit -m "Week 1: Ticket Triage"`, `git push -u origin week01`, then open a PR from `week01` into `main`, fill in the template and request a review from `@ravick` (Reviewers, on the right of the PR). When it's approved, you merge it.

Expect six to eight hours in total, including the learning. Due before Session 02. Your mentor announces the date.

## House rule

Never submit code you cannot explain. A mentor may point at any line and ask "why?".

## Optional stretch

Wrap `triage()` in a small FastAPI endpoint. That is Week 2's job, so only if you have energy to spare.
