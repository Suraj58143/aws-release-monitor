"""Normalize source records into the stable dashboard data model."""

from __future__ import annotations

from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from time import struct_time
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from collector.classification import classify
from collector.storage import article_hash

_TRACKING_PARAMETERS = {"fbclid", "gclid"}


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    else:
        text = unescape(text)
    return " ".join(text.split())


def _normalize_url(value: object, base_url: str) -> str:
    raw_url = _clean_text(value)
    if not raw_url:
        return ""
    parts = urlsplit(urljoin(base_url, raw_url))
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return ""
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_PARAMETERS
    ]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", urlencode(query), ""))


def _normalize_date(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day, tzinfo=UTC)
    elif isinstance(value, struct_time):
        parsed = datetime(*value[:6], tzinfo=UTC)
    else:
        raw_date = str(value).strip()
        try:
            parsed = datetime.fromisoformat(raw_date)
        except ValueError:
            try:
                parsed = parsedate_to_datetime(raw_date)
            except (TypeError, ValueError, OverflowError):
                for date_format in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
                    try:
                        parsed = datetime.strptime(raw_date, date_format).replace(tzinfo=UTC)
                        break
                    except ValueError:
                        continue
                else:
                    return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_article(raw: dict[str, object]) -> dict[str, str] | None:
    """Normalize one source item; return None when it lacks a title or valid URL."""
    title = _clean_text(raw.get("title"))
    url = _normalize_url(raw.get("url"), str(raw.get("base_url", "")))
    if not title or not url:
        return None

    summary = _clean_text(raw.get("summary"))[:1000]
    source = _clean_text(raw.get("source")) or "AWS"
    category = "Security" if "security bulletin" in source.casefold() else classify(title, summary)
    article = {
        "title": title,
        "url": url,
        "source": source,
        "category": category,
        "summary": summary,
        "published": _normalize_date(raw.get("publish_date")),
    }
    article["hash"] = article_hash(article["title"], article["url"])
    return article
