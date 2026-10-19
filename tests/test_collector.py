from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest

from collector import storage
from collector.classification import classify
from collector.normalize import normalize_article


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Security bulletin for Amazon S3", "Security"),
        ("New version 2 upgrade for the CLI", "Upgrade"),
        ("Fixed issue in service console", "Bug Fix"),
        ("Introducing a new database service", "Release"),
        ("New region availability update", "Service Update"),
    ],
)
def test_classification_prioritizes_specific_categories(title: str, expected: str) -> None:
    assert classify(title) == expected


def test_non_security_release_is_not_misclassified_by_summary_context() -> None:
    assert classify(
        "Introducing an AWS architecture assistant",
        "Recommendations include cost, security, performance, and resilience.",
    ) == "Release"


def test_normalize_article_cleans_url_text_and_date() -> None:
    article = normalize_article(
        {
            "title": "<b>Launch of a new AWS feature</b>",
            "url": "/about-aws/whats-new/item/?utm_source=news#details",
            "source": "AWS What's New",
            "summary": "<p>A new feature is now available.</p>",
            "publish_date": "2026-10-19T10:30:00+00:00",
            "base_url": "https://aws.amazon.com/new/",
        }
    )

    assert article is not None
    assert article["title"] == "Launch of a new AWS feature"
    assert article["url"] == "https://aws.amazon.com/about-aws/whats-new/item/"
    assert article["summary"] == "A new feature is now available."
    assert article["published"] == "2026-10-19T10:30:00Z"
    assert len(article["hash"]) == 64


def test_normalize_article_rejects_invalid_records() -> None:
    assert normalize_article({"title": "No URL", "base_url": "https://aws.amazon.com"}) is None
    assert normalize_article({"title": "Bad URL", "url": "javascript:alert(1)"}) is None


def test_article_hash_matches_required_sha256_pair() -> None:
    title, url = "AWS announcement", "https://aws.amazon.com/update/"
    expected = hashlib.sha256(f"{title}{url}".encode()).hexdigest()
    assert storage.article_hash(title, url) == expected


def test_security_bulletin_source_sets_security_category() -> None:
    article = normalize_article(
        {
            "title": "Bulletin 2026-123",
            "url": "https://aws.amazon.com/security/security-bulletins/example/",
            "source": "AWS Security Bulletins",
        }
    )
    assert article is not None
    assert article["category"] == "Security"


def test_save_results_deduplicates_and_preserves_history(tmp_path, monkeypatch) -> None:
    articles_path = tmp_path / "articles.json"
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(storage, "ARTICLES_PATH", articles_path)
    monkeypatch.setattr(storage, "STATE_PATH", state_path)
    prior = {
        "title": "Earlier AWS release",
        "url": "https://aws.amazon.com/earlier/",
        "source": "AWS What's New",
        "category": "Release",
        "summary": "",
        "published": "2026-01-01T00:00:00Z",
        "hash": storage.article_hash("Earlier AWS release", "https://aws.amazon.com/earlier/"),
    }
    articles_path.write_text(json.dumps([prior]), encoding="utf-8")
    new = {
        "title": "Current AWS release",
        "url": "https://aws.amazon.com/current/",
        "source": "AWS What's New",
        "category": "Release",
        "summary": "",
        "published": "2026-10-19T00:00:00Z",
        "hash": "",
    }
    duplicate = {**new, "category": "Security", "summary": "Corrected security bulletin summary"}

    added, total = storage.save_results([new, duplicate], {"AWS What's New": {"status": "ok"}})

    assert (added, total) == (1, 2)
    stored = json.loads(articles_path.read_text(encoding="utf-8"))
    assert stored[0]["title"] == "Current AWS release"
    assert stored[0]["category"] == "Security"
    assert stored[0]["summary"] == "Corrected security bulletin summary"
    assert stored[1]["title"] == "Earlier AWS release"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["total_articles"] == 2
    assert datetime.fromisoformat(state["last_run"]).tzinfo == UTC
