"""Run Ticket Triage from the command line.

Examples (from the repo root; on Windows use `python`, on Mac `python3` also works):
    python week01/triage/run.py                      all 12 tickets
    python week01/triage/run.py --eval               compare with expected.jsonl, print accuracy
    python week01/triage/run.py --ticket 4 --repeat 5 --temperature 1.0     variation experiment
    python week01/triage/run.py --fake               no API key needed (a crude keyword guesser)
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from llm import DemoClient, GeminiClient, ModelCallError, ModelClient
from models import Triage, TriageError
from triage import DEFAULT_TRACE_DIR, triage

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Triage the sample support tickets.")
    p.add_argument("--eval", action="store_true", help="compare with expected.jsonl and print accuracy")
    p.add_argument("--ticket", type=int, metavar="N", help="only ticket number N")
    p.add_argument("--repeat", type=int, default=1, metavar="K", help="run each ticket K times (default 1)")
    p.add_argument("--temperature", type=float, default=0.2, metavar="T", help="model temperature (default 0.2)")
    p.add_argument("--fake", action="store_true", help="use the offline demo guesser instead of Gemini")
    return p.parse_args()


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [max(len(str(cell)) for cell in column) for column in zip(headers, *rows)]
    line = "-+-".join("-" * w for w in widths)
    print(" | ".join(h.ljust(w) for h, w in zip(headers, widths)).rstrip())
    print(line)
    for row in rows:
        print(" | ".join(str(cell).ljust(w) for cell, w in zip(row, widths)).rstrip())


def shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def triage_all(tickets: list[dict], client: ModelClient, args: argparse.Namespace) -> list[tuple[dict, int, Triage | str]]:
    """Run every ticket `repeat` times. A failure becomes an error string, so one bad ticket does not stop the run."""
    outcomes = []
    for ticket in tickets:
        for run in range(1, args.repeat + 1):
            try:
                outcome = triage(ticket["text"], client, temperature=args.temperature)
            except (TriageError, ModelCallError) as exc:
                outcome = str(exc)
            outcomes.append((ticket, run, outcome))
    return outcomes


def show_plain(outcomes, repeat: int) -> None:
    headers = ["ID"] + (["Run"] if repeat > 1 else []) + ["Category", "Priority", "Human?", "Summary"]
    rows = []
    for ticket, run, outcome in outcomes:
        lead = [str(ticket["id"])] + ([str(run)] if repeat > 1 else [])
        if isinstance(outcome, Triage):
            rows.append(lead + [outcome.category, outcome.priority, "yes" if outcome.needs_human else "no", shorten(outcome.summary, 60)])
        else:
            rows.append(lead + ["ERROR", "-", "-", shorten(outcome, 60)])
    print_table(headers, rows)


def show_eval(outcomes, expected: dict[int, dict], repeat: int) -> None:
    headers = ["ID"] + (["Run"] if repeat > 1 else []) + ["Category", "Expected", "Priority", "Expected", "Match"]
    rows, category_hits, priority_hits, notes = [], 0, 0, {}
    for ticket, run, outcome in outcomes:
        want = expected[ticket["id"]]
        lead = [str(ticket["id"])] + ([str(run)] if repeat > 1 else [])
        if isinstance(outcome, Triage):
            cat_ok, pri_ok = outcome.category == want["category"], outcome.priority == want["priority"]
            category_hits += cat_ok
            priority_hits += pri_ok
            match = "ok" if cat_ok and pri_ok else "+".join(n for n, good in (("category", cat_ok), ("priority", pri_ok)) if not good)
            rows.append(lead + [outcome.category, want["category"], outcome.priority, want["priority"], match])
            if not (cat_ok and pri_ok) and "note" in want:
                notes[ticket["id"]] = want["note"]
        else:
            rows.append(lead + ["ERROR", want["category"], "-", want["priority"], "error"])
    print_table(headers, rows)
    total = len(outcomes)
    print(f"\nCategory accuracy: {category_hits}/{total} ({category_hits / total:.0%})")
    print(f"Priority accuracy: {priority_hits}/{total} ({priority_hits / total:.0%})")
    for ticket_id, note in notes.items():
        print(f"Note on ticket {ticket_id}: {note}")


def show_variation(outcomes) -> None:
    """For --repeat: did the answers change from run to run?"""
    print("\nVariation across runs:")
    by_ticket: dict[int, list[Triage]] = {}
    for ticket, _, outcome in outcomes:
        if isinstance(outcome, Triage):
            by_ticket.setdefault(ticket["id"], []).append(outcome)
    for ticket_id, results in by_ticket.items():
        labels = Counter(f"{r.category} {r.priority}" for r in results)
        label_text = ", ".join(f"{count}x {label}" for label, count in labels.most_common())
        distinct = len({r.summary for r in results})
        print(f"  Ticket {ticket_id}: {label_text}; {distinct} different summaries in {len(results)} runs")


def main() -> int:
    args = parse_args()
    if args.repeat < 1:
        print("--repeat must be at least 1")
        return 2

    tickets = load_jsonl(DATA_DIR / "tickets.jsonl")
    if args.ticket is not None:
        tickets = [t for t in tickets if t["id"] == args.ticket]
        if not tickets:
            print(f"There is no ticket {args.ticket}. Ticket ids are 1 to 12.")
            return 2

    try:
        client = DemoClient() if args.fake else GeminiClient()
    except ModelCallError as exc:
        print(exc)
        return 1

    print(f"Model: {client.model_name} | temperature: {args.temperature} | tickets: {len(tickets)} | runs each: {args.repeat}\n")
    try:
        outcomes = triage_all(tickets, client, args)
    except NotImplementedError as exc:
        print(f"{exc}\nOpen week01/triage/triage.py and work through the TODOs, then run again.")
        return 2

    if args.eval:
        expected = {row["id"]: row for row in load_jsonl(DATA_DIR / "expected.jsonl")}
        show_eval(outcomes, expected, args.repeat)
    else:
        show_plain(outcomes, args.repeat)
    if args.repeat > 1:
        show_variation(outcomes)

    errors = sum(isinstance(o, str) for _, _, o in outcomes)
    if errors:
        print(f"\n{errors} run(s) failed. First error: {next(o for _, _, o in outcomes if isinstance(o, str))}")
    print(f"\nTraces are in {DEFAULT_TRACE_DIR}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
