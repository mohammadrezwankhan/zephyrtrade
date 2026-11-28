#!/usr/bin/env python3
"""Fail closed when a PR range has AI-attributed commits."""

import os
import re
import shutil
import subprocess
import sys

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
NAME_TOKEN_RE = re.compile(r"\b(?:codex|grok)\b", re.IGNORECASE)
CLAUDE_TOOL_RE = re.compile(
    r"\bclaude(?:[ _/-]+(?:code|agent|bot|opus|sonnet|haiku|gpt|[0-9][a-z0-9.-]*))\b"
    r"|\banthropic[ /-]+claude\b",
    re.IGNORECASE,
)
CLAUDE_BARE_RE = re.compile(r"^claude$", re.IGNORECASE)
EMAIL_BOT_RE = re.compile(
    r"(?:^|[+._-])(?:codex(?:-agent)?|claude(?:-code)?|grok)(?:\[bot\])?$",
    re.IGNORECASE,
)
VENDOR_NOREPLY_RE = re.compile(
    r"^noreply@(openai\.com|anthropic\.com|x\.ai)$", re.IGNORECASE
)


class InspectionError(RuntimeError):
    """Raised when commit metadata cannot be inspected safely."""

    pass


def git(*args, input_text=None):
    """Run a fixed Git plumbing command without invoking a shell."""
    git_executable = shutil.which("git")
    if git_executable is None:
        raise InspectionError(
            "Unable to inspect commits: Git executable is unavailable"
        )
    # Fixed Git plumbing; only validated object IDs reach this subprocess.
    result = subprocess.run(  # noqa: S603
        [git_executable, *args], input=input_text, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if result.returncode:
        detail = result.stderr.strip() or (
            f"git {' '.join(args)} exited {result.returncode}"
        )
        raise InspectionError(detail)
    return result.stdout


def prohibited_identity(value):
    """Return whether a name/email identifies a prohibited AI author."""
    name, sep, address = value.rpartition("<")
    if sep and address.endswith(">"):
        name = name.strip()
        address = address[:-1].strip()
    else:
        name = value.strip()
        address = ""

    if (
        NAME_TOKEN_RE.search(name)
        or CLAUDE_TOOL_RE.search(name)
        or CLAUDE_BARE_RE.fullmatch(name)
    ):
        return True

    if address:
        local, at, _domain = address.rpartition("@")
        if at and (EMAIL_BOT_RE.search(local) or VENDOR_NOREPLY_RE.fullmatch(address)):
            return True
        if address.casefold().endswith("@users.noreply.github.com") and re.search(
            r"(?:^|[+._-])(?:codex|claude|grok)\[bot\]$", local, re.IGNORECASE
        ):
            return True
    return False


def event_range(event_name):
    """Return the event's validated base-to-head commit range."""
    if event_name == "pull_request":
        base = os.environ.get("PR_BASE_SHA", "")
        head = os.environ.get("PR_HEAD_SHA", "")
    elif event_name == "merge_group":
        base = os.environ.get("MERGE_BASE_SHA", "")
        head = os.environ.get("MERGE_HEAD_SHA", "")
    else:
        raise InspectionError(
            f"Unsupported event for authorship inspection: {event_name!r}"
        )
    if not SHA_RE.fullmatch(base) or not SHA_RE.fullmatch(head):
        raise InspectionError(
            "Unable to inspect commits: event base/head SHA is missing or malformed"
        )
    for sha in (base, head):
        try:
            git("cat-file", "-e", f"{sha}^{{commit}}")
        except InspectionError as exc:
            raise InspectionError(
                f"Unable to inspect commits: event SHA {sha} is not a commit"
            ) from exc
    return f"{base}..{head}"


def commit_details(commit):
    """Return an inspected commit's author, committer, and message."""
    raw = git("show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce%x00%B", commit)
    parts = raw.split("\x00", 4)
    if len(parts) != 5:
        raise InspectionError(f"Unable to inspect commit metadata for {commit}")
    author_name, author_email, committer_name, committer_email, message = parts
    metadata = (author_name, author_email, committer_name, committer_email)
    if not all(part.strip() for part in metadata):
        raise InspectionError(
            f"Unable to inspect complete author/committer metadata for {commit}"
        )
    return (
        f"{author_name.strip()} <{author_email.strip()}>",
        f"{committer_name.strip()} <{committer_email.strip()}>",
        message,
    )


def coauthor_trailers(message):
    """Parse Co-authored-by trailers from a commit message."""
    parsed = git("interpret-trailers", "--parse", input_text=message)
    trailers = []
    for line in parsed.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            raise InspectionError("Unable to inspect parsed commit trailers")
        if key.strip().casefold() == "co-authored-by":
            if not value.strip():
                raise InspectionError(
                    "Unable to inspect an empty Co-authored-by trailer"
                )
            trailers.append(value.strip())
    return trailers


def inspect():
    """Validate every commit in the event range."""
    commit_range = event_range(os.environ.get("EVENT_NAME", ""))
    output = git("rev-list", "--reverse", "--topo-order", commit_range)
    commits = [line for line in output.splitlines() if line]
    if not commits:
        raise InspectionError(
            "Unable to inspect commits: event range contains no commits"
        )

    violations = []
    for commit in commits:
        if not SHA_RE.fullmatch(commit):
            raise InspectionError(
                "Unable to inspect commits: git returned a malformed commit ID"
            )
        author, committer, message = commit_details(commit)
        if prohibited_identity(author):
            violations.append(f"{commit}: AI author identity {author!r}")
        if prohibited_identity(committer):
            violations.append(f"{commit}: AI committer identity {committer!r}")
        violations.extend(
            f"{commit}: prohibited AI Co-authored-by trailer {trailer!r}"
            for trailer in coauthor_trailers(message)
            if prohibited_identity(trailer)
        )

    if violations:
        for violation in violations:
            sys.stderr.write(f"{violation}\n")
        raise InspectionError(
            "AI tools may be disclosed in prose, but must not be recorded as authors, "
            "committers, or co-authors."
        )
    sys.stdout.write(
        f"Checked {len(commits)} commit(s); human-authorship metadata policy passed.\n"
    )


if __name__ == "__main__":
    try:
        inspect()
    except InspectionError as exc:
        sys.stderr.write(f"human-authorship policy error: {exc}\n")
        sys.exit(1)
