# EXPLAIN: Ticket Triage

Answer first. Write for a mentor who has not seen your code. Short sentences. Replace every line in angle brackets.

## 1. What it does, in one sentence
Classifies customer support tickets into validated categories and priorities using the Gemini API, retrying once with error feedback on validation failure and recording every attempt to a trace log.

## 2. Walk-through of every line I did not type myself
For each block of code that you did not write (from your assistant, a tutorial or the starter), say what it does and why it is there. If you cannot, that block is not ready to submit.

| Where (file and lines) | What it does | Why it is there |
|---|---|---|
| `triage.py`, lines 70–93 (`_write_trace`) | Creates date-stamped `.jsonl` files and writes structured metadata (`timestamp`, `model`, `attempt`, `latency_ms`, `ok`, `error`, `input_chars`). | Provides full auditability and latency observability for every model call attempt. |
| `triage.py`, lines 122–144 (`triage` loop & validation) | Wraps ticket in `<ticket>` tags, calls `client.generate_json()`, times the call, and parses via `Triage.model_validate_json()`. | Guarantees raw LLM text is strictly validated against our Pydantic schema before returning. |
| `triage.py`, lines 145–164 (Error handling & retry) | Catches `(ValidationError, ValueError)`, logs failure, constructs an informed prompt with the exact error for attempt 2, or raises `TriageError`. | Allows the model to self-correct formatting or schema mistakes, and ensures bad data is never passed downstream. |

## 3. Why do outputs vary?
Language models sample the next token based on a probability distribution rather than producing fixed outputs. A higher temperature (e.g., 1.0) flattens the distribution, allowing less probable tokens to be chosen, which introduces lexical variation into the summary and rationale. A temperature of 0 picks the most probable token greedily at each step, producing consistent and deterministic classifications.

## 4. What the retry protects against, and what it does not
- Protects against: Malformed JSON strings, invalid categories or priorities outside the enum, missing schema fields, and summaries exceeding the 25-word limit.
- Does not protect against: Network disconnections, API quota exhaustion (such as HTTP 429 errors), prompt injection, or tickets where the model misclassifies customer intent despite producing schema-valid JSON.

## 5. One thing that broke, and how I found it
- **What did you see?** Running `python week01/triage/run.py --eval` succeeded for tickets 1–6, then failed on ticket 7 with `Gemini API error 429: You exceeded your current quota`.
- **What did you try first?** Inspected the terminal traceback and the generated traces in `traces/` to see where the run halted.
- **What was the cause?** Google's free tier limits `gemini-3.8-flash` to 5 requests per minute and 20 requests per day. The loop dispatched calls too rapidly without pacing.
- **What did you change?** Added rate-limit pacing (`time.sleep(12)`) and automatic retry with backoff on 429 errors in `run.py`.

## 6. Experiment 1: variation
One ticket (number <>), five runs each.

| Temperature | Labels across 5 runs | Different summaries | What changed |
|---|---|---|---|
| 1.0 | | | |
| 0 | | | |

## 7. Experiment 2: context
The one change I made to `SYSTEM_INSTRUCTION`: <>

| | Category accuracy | Priority accuracy |
|---|---|---|
| Before | /12 | /12 |
| After | /12 | /12 |

What I think explains the difference: <>
