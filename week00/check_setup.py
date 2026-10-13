"""Check that this machine is ready for the Fellowship.

Run it from anywhere inside your repo:
    python week00/check_setup.py          (Windows and Mac)
    python week00/check_setup.py --ping   (also makes one tiny real Gemini call)

Each line starts with PASS, WARN or FAIL. Fix every FAIL. A WARN is worth reading but
will not stop you. Your API key is never printed, not even a part of it.
"""

import argparse
import importlib
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
MIN_PYTHON = (3, 12)
RECOMMENDED_PYTHON = "3.14"
REPO_ROOT = Path(__file__).resolve().parent.parent
# Keep in step with DEFAULT_MODEL in week01/triage/llm.py.
DEFAULT_MODEL = "gemini-3.8-flash"
PACKAGES = {"google.genai": "google-genai", "pydantic": "pydantic", "dotenv": "python-dotenv", "pytest": "pytest"}


@dataclass
class Result:
    status: str
    name: str
    detail: str = ""
    hint: str = ""


def git(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=20)


def check_python() -> Result:
    major, minor = sys.version_info[:2]
    text = f"{major}.{minor}"
    if (major, minor) < MIN_PYTHON:
        return Result(FAIL, "Python version", f"{text} is too old", f"Install Python {RECOMMENDED_PYTHON} (3.12 or newer works).")
    if text != RECOMMENDED_PYTHON:
        return Result(PASS, "Python version", f"{text} (works; {RECOMMENDED_PYTHON} is recommended)")
    return Result(PASS, "Python version", text)


def check_virtualenv() -> Result:
    if sys.prefix == sys.base_prefix:
        return Result(WARN, "Virtual environment", "not active", "Create and activate .venv as the README shows, so packages stay inside this project.")
    return Result(PASS, "Virtual environment", "active")


def check_git_installed() -> Result:
    if not shutil.which("git"):
        return Result(FAIL, "Git installed", "git not found", "Install Git, then open a new terminal.")
    return Result(PASS, "Git installed", git("--version").stdout.strip())


def check_git_identity() -> list[Result]:
    results = []
    for key in ("user.name", "user.email"):
        value = git("config", key).stdout.strip() if shutil.which("git") else ""
        if value:
            results.append(Result(PASS, f"git {key}", "set"))
        else:
            results.append(Result(FAIL, f"git {key}", "not set", f'Run: git config --global {key} "your value"'))
    return results


def check_git_repo() -> list[Result]:
    if not shutil.which("git"):
        return [Result(FAIL, "Inside a git repo", "git not available")]
    inside = git("rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0:
        return [Result(FAIL, "Inside a git repo", "this folder is not a git repo", "Clone your repo from GitHub (see the README), do not download a ZIP.")]
    remote = git("remote", "get-url", "origin")
    if remote.returncode != 0:
        return [
            Result(PASS, "Inside a git repo", "yes"),
            Result(FAIL, "Remote called origin", "none", "Clone your repo from GitHub so origin points at it."),
        ]
    return [Result(PASS, "Inside a git repo", "yes"), Result(PASS, "Remote called origin", remote.stdout.strip())]


def check_packages() -> list[Result]:
    results = []
    for module, package in PACKAGES.items():
        try:
            importlib.import_module(module)
            results.append(Result(PASS, f"Package {package}", "importable"))
        except ImportError:
            results.append(Result(FAIL, f"Package {package}", "not installed", "Activate .venv, then run: pip install -r requirements.txt"))
    return results


def read_key(root: Path) -> str:
    """Return the key from .env, or '' if there is none. The caller must never print it."""
    from dotenv import dotenv_values

    return (dotenv_values(root / ".env", encoding="utf-8-sig").get("GEMINI_API_KEY") or "").strip()


def check_env_key(root: Path = REPO_ROOT) -> Result:
    name = ".env with GEMINI_API_KEY"
    if not (root / ".env").exists():
        return Result(WARN, name, ".env not found", "Copy .env.example to .env and paste your key. You need it for the Week 1 build, not for setup.")
    try:
        key = read_key(root)
    except ImportError:
        return Result(WARN, name, "cannot check (python-dotenv missing)", "Install the packages first.")
    if not key:
        return Result(WARN, name, "GEMINI_API_KEY is empty", "Get a key at https://aistudio.google.com/apikey and paste it after the = sign.")
    return Result(PASS, name, "key present (not shown)")


def check_env_ignored(root: Path = REPO_ROOT) -> Result:
    name = ".env is git-ignored"
    if not shutil.which("git"):
        return Result(WARN, name, "cannot check without git")
    tracked = git("ls-files", "--error-unmatch", ".env", cwd=root)
    if tracked.returncode == 0:
        return Result(FAIL, name, ".env is TRACKED by git", "Stop and ask your mentor. Run: git rm --cached .env  then rotate your key.")
    ignored = git("check-ignore", "-q", ".env", cwd=root)
    if ignored.returncode == 0:
        return Result(PASS, name, "yes")
    if ignored.returncode == 1:
        return Result(FAIL, name, "NOT ignored", "Add a line .env to .gitignore before you create the file.")
    return Result(WARN, name, "cannot check (not a git repo?)")


def offline_checks() -> list[Result]:
    results = [check_python(), check_virtualenv(), check_git_installed(), *check_git_identity(), *check_git_repo(), *check_packages()]
    results += [check_env_key(), check_env_ignored()]
    return results


def ping_gemini(root: Path = REPO_ROOT) -> Result:
    name = "Gemini API reachable"
    try:
        key = read_key(root)
    except ImportError:
        return Result(FAIL, name, "python-dotenv missing", "Install the packages first.")
    if not key:
        return Result(FAIL, name, "no key to try", "Put your key in .env first.")
    model = os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
    try:
        from google import genai

        client = genai.Client(api_key=key)  # keep a name for it: a throwaway client closes itself too early
        started = time.perf_counter()
        client.models.generate_content(model=model, contents="Reply with the single word: ready")
        millis = round((time.perf_counter() - started) * 1000)
        return Result(PASS, name, f"{model} answered in {millis} ms")
    except Exception as exc:  # any failure is a useful message here
        message = str(exc).replace(key, "***")[:200]
        return Result(FAIL, name, f"{type(exc).__name__}: {message}", "Check the key, your internet, and https://aistudio.google.com for quota.")


def print_results(results: list[Result]) -> None:
    for r in results:
        print(f"[{r.status}] {r.name}" + (f": {r.detail}" if r.detail else ""))
        if r.hint and r.status != PASS:
            print(f"       -> {r.hint}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check your Fellowship setup.")
    parser.add_argument("--ping", action="store_true", help="make one tiny real Gemini call and report the latency")
    args = parser.parse_args()

    print("Fellowship setup check\n")
    results = offline_checks()
    if args.ping:
        results.append(ping_gemini())
    print_results(results)

    counts = {s: sum(r.status == s for r in results) for s in (PASS, WARN, FAIL)}
    print(f"\n{counts[PASS]} passed, {counts[WARN]} warnings, {counts[FAIL]} failed.")
    if counts[FAIL]:
        print("Fix the FAIL lines and run this again. If you are stuck, paste the output (it contains no secrets) to your mentor.")
        return 1
    print("You are ready." if not counts[WARN] else "You can go on. Read the WARN lines when you have a minute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
