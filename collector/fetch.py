"""Fetch AWS announcement sources and persist normalized records."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlsplit

import feedparser
import requests
from bs4 import BeautifulSoup

from collector.normalize import normalize_article
from collector.storage import save_results

LOGGER = logging.getLogger("aws_release_monitor")
USER_AGENT = "aws-release-monitor/1.0 (+https://github.com/Suraj58143/aws-release-monitor)"
REQUEST_TIMEOUT = (10, 30)

# Add future sources here. HTML sources may specify a path regular expression;
# feed sources should provide the official RSS/Atom feed URL.
SOURCES = (
    {
        "name": "AWS What's New",
        "url": "https://aws.amazon.com/new/",
        "feed_url": "https://aws.amazon.com/about-aws/whats-new/recent/feed/",
        "kind": "rss",
    },
    {
        "name": "AWS News Blog",
        "url": "https://aws.amazon.com/blogs/aws/",
        "feed_url": "https://aws.amazon.com/blogs/aws/feed/",
        "kind": "rss",
    },
    {
        "name": "AWS Security Bulletins",
        "url": "https://aws.amazon.com/security/security-bulletins/",
        "feed_url": "https://aws.amazon.com/security/security-bulletins/rss/feed/",
        "kind": "rss",
    },
)


def _parse_html_source(
    html: str,
    base_url: str,
    source_name: str,
    path_pattern: str,
) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    path_match = re.compile(path_pattern, re.IGNORECASE)
    seen_urls: set[str] = set()
    records: list[dict[str, object]] = []

    for anchor in soup.find_all("a", href=True):
        absolute_url = urljoin(base_url, str(anchor["href"]))
        parts = urlsplit(absolute_url)
        if parts.scheme not in {"http", "https"} or not path_match.search(parts.path):
            continue
        if parts.netloc.lower() not in {"aws.amazon.com", "www.aws.amazon.com"}:
            continue

        container = anchor.find_parent("article") or anchor.find_parent("li") or anchor.parent
        heading = anchor.find(["h1", "h2", "h3", "h4"])
        if heading is None and container is not None:
            heading = container.find(["h1", "h2", "h3", "h4"])
        title = (heading or anchor).get_text(" ", strip=True)
        title = " ".join(title.split())
        if len(title) < 8 or title.casefold() in {"read more", "learn more", "see more"}:
            continue
        normalized_url = parts._replace(fragment="").geturl()
        if normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)

        summary = ""
        published: object = ""
        if container is not None:
            paragraph = container.find("p")
            if paragraph:
                summary = paragraph.get_text(" ", strip=True)
            time_element = container.find("time")
            if time_element:
                published = time_element.get("datetime") or time_element.get_text(" ", strip=True)

        records.append(
            {
                "title": title,
                "url": normalized_url,
                "source": source_name,
                "summary": summary,
                "publish_date": published,
                "base_url": base_url,
            }
        )
    return records


def _fetch_source(session: requests.Session, source: dict[str, str]) -> list[dict[str, object]]:
    if source["kind"] == "rss":
        response = session.get(source["feed_url"], timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        records = []
        for entry in parsed.entries:
            records.append(
                {
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "source": source["name"],
                    "summary": entry.get("summary", ""),
                    "publish_date": entry.get("published_parsed") or entry.get("updated_parsed") or "",
                    "base_url": source["url"],
                }
            )
        if not records and not parsed.bozo:
            raise ValueError("The RSS feed contained no entries")
        if parsed.bozo and not records:
            raise ValueError(f"The RSS feed could not be parsed: {parsed.bozo_exception}")
        return records

    response = session.get(source["url"], timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    records = _parse_html_source(
        response.text,
        response.url,
        source["name"],
        source["path_pattern"],
    )
    if not records:
        raise ValueError("No matching announcement links were found on the source page")
    return records


def collect() -> tuple[int, int]:
    """Fetch all sources, retain successful-source results, and save state."""
    raw_articles: list[dict[str, object]] = []
    source_status: dict[str, dict[str, Any]] = {}

    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/atom+xml,application/rss+xml"})
        for source in SOURCES:
            try:
                raw_records = _fetch_source(session, source)
                normalized = [
                    article
                    for raw in raw_records
                    if (article := normalize_article(raw)) is not None
                ]
                raw_articles.extend(normalized)
                filtered_out = len(raw_records) - len(normalized)
                source_status[source["name"]] = {
                    "url": source["url"],
                    "status": "ok",
                    "fetched": len(raw_records),
                    "normalized": len(normalized),
                    "filtered_out": filtered_out,
                    "error": "",
                }
                LOGGER.info(
                    "%s: retained %d service-specific announcements; filtered %d of %d",
                    source["name"],
                    len(normalized),
                    filtered_out,
                    len(raw_records),
                )
            except (requests.RequestException, ValueError, KeyError) as error:
                source_status[source["name"]] = {
                    "url": source["url"],
                    "status": "error",
                    "fetched": 0,
                    "normalized": 0,
                    "filtered_out": 0,
                    "error": str(error),
                }
                LOGGER.exception("Failed to collect %s", source["name"])

    if not any(item["status"] == "ok" for item in source_status.values()):
        raise RuntimeError("All AWS announcement sources failed; existing dataset was left unchanged")

    added, total = save_results(raw_articles, source_status)
    LOGGER.info(
        "Collection finished at %s: %d new announcements, %d historical records",
        datetime.now(UTC).isoformat(timespec="seconds"),
        added,
        total,
    )
    return added, total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    collect()
