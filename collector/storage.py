"""Persistent JSON storage and SHA-256 deduplication."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from collector.services import service_for_title

ROOT = Path(__file__).resolve().parent.parent
ARTICLES_PATH = ROOT / "data" / "articles.json"
STATE_PATH = ROOT / "data" / "state.json"


def article_hash(title: str, url: str) -> str:
    """Hash the exact normalized title-plus-URL pair."""
    return hashlib.sha256(f"{title}{url}".encode()).hexdigest()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open(encoding="utf-8") as source:
            return json.load(source)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read JSON data from {path}: {error}") from error


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary_path = output.name
            json.dump(value, output, ensure_ascii=False, indent=2)
            output.write("\n")
        os.replace(temporary_path, path)
    except OSError as error:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
        raise RuntimeError(f"Cannot write JSON data to {path}: {error}") from error


def load_articles() -> list[dict[str, str]]:
    articles = _read_json(ARTICLES_PATH, [])
    if not isinstance(articles, list) or any(not isinstance(item, dict) for item in articles):
        raise RuntimeError(f"{ARTICLES_PATH} must contain a JSON array of article objects")
    return articles


def save_results(
    new_articles: list[dict[str, str]],
    source_status: dict[str, dict[str, Any]],
) -> tuple[int, int]:
    """Merge new records into history and persist article and run metadata."""
    articles = []
    for article in load_articles():
        service = service_for_title(article.get("title", ""))
        if service is not None:
            article["service"] = service
            articles.append(article)
    known_articles = {item.get("hash"): index for index, item in enumerate(articles)}
    added = 0
    for article in new_articles:
        digest = article_hash(article["title"], article["url"])
        article["hash"] = digest
        if digest not in known_articles:
            known_articles[digest] = len(articles)
            articles.append(article)
            added += 1
            continue

        existing = articles[known_articles[digest]]
        for field in ("title", "url", "source", "service", "category", "hash"):
            existing[field] = article[field]
        for field in ("summary", "published"):
            if article[field]:
                existing[field] = article[field]

    articles.sort(key=lambda item: (item.get("published", ""), item.get("title", "").casefold()), reverse=True)
    _write_json(ARTICLES_PATH, articles)

    previous_state = _read_json(STATE_PATH, {})
    if not isinstance(previous_state, dict):
        raise TypeError(f"{STATE_PATH} must contain a JSON object")
    state = {
        "last_run": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "total_articles": len(articles),
        "new_articles": added,
        "sources": source_status,
    }
    _write_json(STATE_PATH, state)
    return added, len(articles)
