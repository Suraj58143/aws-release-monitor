"""Keyword-based categorization for AWS announcements."""

import re

CATEGORIES = (
    "Release",
    "Upgrade",
    "Security",
    "Bug Fix",
    "Service Update",
    "General Announcement",
)

_SECURITY_PATTERN = re.compile(
    r"\b(security|vulnerabilit(?:y|ies)|cve-\d{4}-\d+|bulletin|patch(?:ed)?)\b",
    re.IGNORECASE,
)
_SECURITY_SUMMARY_PATTERN = re.compile(
    r"\b(security (?:bulletin|advisory|update|patch|vulnerabilit(?:y|ies)|issue)|"
    r"vulnerabilit(?:y|ies)|cve-\d{4}-\d+|bulletin)\b",
    re.IGNORECASE,
)

_RULES = (
    (
        "Upgrade",
        re.compile(
            r"\b(upgrade|upgraded|upgrading|migration|migrate|version \d|now supports)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Bug Fix",
        re.compile(
            r"\b(bug fix|bugfix|fixed|fixes|fix for|resolves|resolved|issue with)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Release",
        re.compile(
            r"\b(launch(?:es|ed)?|introducing|announcing|now available|general availability|preview)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Service Update",
        re.compile(
            r"\b(pricing|quota|limit|region|availability|support for|maintenance|updated)\b",
            re.IGNORECASE,
        ),
    ),
)


def classify(title: str, summary: str = "") -> str:
    """Return the first matching category, prioritizing security and fixes."""
    if _SECURITY_PATTERN.search(title) or _SECURITY_SUMMARY_PATTERN.search(summary):
        return "Security"
    text = f"{title} {summary}"
    for category, pattern in _RULES:
        if pattern.search(text):
            return category
    return "General Announcement"
