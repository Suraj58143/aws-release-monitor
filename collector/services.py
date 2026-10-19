"""AWS-owned service matching and third-party announcement exclusions."""

from __future__ import annotations

import json
import re
from pathlib import Path

_CATALOG_PATH = Path(__file__).resolve().parent / "services.json"
with _CATALOG_PATH.open(encoding="utf-8") as catalog_file:
    _CATALOG: dict[str, list[str]] = json.load(catalog_file)

_SERVICE_PATTERNS = tuple(
    (
        service,
        re.compile(
            r"(?<![A-Za-z0-9])(?:"
            + "|".join(
                re.escape(alias)
                for alias in sorted({service, *aliases}, key=len, reverse=True)
            )
            + r")(?![A-Za-z0-9])",
            re.IGNORECASE,
        ),
    )
    for service, aliases in sorted(
        _CATALOG.items(),
        key=lambda entry: max(map(len, [entry[0], *entry[1]])),
        reverse=True,
    )
)

_THIRD_PARTY_PATTERN = re.compile(
    r"\b("
    r"anthropic|claude|cohere|databricks|deepseek|elastic\s+cloud|"
    r"google(?:\s+cloud)?|gpt(?:-\d+(?:\.\d+)*)?|hugging\s+face|ibm|"
    r"linux\s+kernel|meta|muse\s+spark|ubuntu|debian|sql\s+server|"
    r"microsoft|mistral(?:\s+ai)?|nemotron|nvidia|openai|oracle|red\s+hat|"
    r"reflection|"
    r"salesforce|snowflake|suse|vercel|vmware|windows(?:\s+server)?"
    r")\b",
    re.IGNORECASE,
)

_GENERAL_POST_PATTERN = re.compile(
    r"\b(weekly roundup|roundup:|all the numbers|celebrating our newest aws heroes|"
    r"reimagines the getting started experience)\b",
    re.IGNORECASE,
)
_THIRD_PARTY_HOSTING_PATTERN = re.compile(
    r"\b(?:available|runs?|hosted|powered|deployed|supported)\s+"
    r"(?:now\s+)?(?:on|in|by)\s*$",
    re.IGNORECASE,
)


def service_for_title(title: str) -> str | None:
    """Return an AWS-owned service when the title is service-specific."""
    if _GENERAL_POST_PATTERN.search(title) or _THIRD_PARTY_PATTERN.search(title):
        return None
    best_service = None
    best_match = None
    best_length = 0
    for service, pattern in _SERVICE_PATTERNS:
        match = pattern.search(title)
        if match and len(match.group()) > best_length:
            best_service = service
            best_match = match
            best_length = len(match.group())
    if best_match and _THIRD_PARTY_HOSTING_PATTERN.search(title[: best_match.start()]):
        return None
    return best_service
