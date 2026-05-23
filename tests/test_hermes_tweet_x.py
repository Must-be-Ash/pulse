from __future__ import annotations

import os

from scripts.lib import env, hermes_tweet_x


def test_parse_search_response_accepts_nested_tweets() -> None:
    response = {
        "data": {
            "tweets": [
                {
                    "id": "123",
                    "text": "Builders are shipping new MCP servers this week",
                    "author": {"username": "builder"},
                    "created_at": "2026-05-23T09:00:00Z",
                    "public_metrics": {
                        "like_count": 12,
                        "retweet_count": 3,
                        "reply_count": 2,
                        "quote_count": 1,
                    },
                }
            ]
        }
    }

    items = hermes_tweet_x.parse_search_response(response, query="MCP servers")

    assert items == [
        {
            "id": "123",
            "text": "Builders are shipping new MCP servers this week",
            "url": "https://x.com/builder/status/123",
            "author_handle": "builder",
            "date": "2026-05-23",
            "engagement": {
                "likes": 12,
                "reposts": 3,
                "replies": 2,
                "quotes": 1,
            },
            "why_relevant": "Hermes Tweet search match for: MCP servers",
            "relevance": 0.75,
        }
    ]


def test_search_x_patches_hermes_tweet_environment(monkeypatch) -> None:
    calls = []

    class FakeHermesTweetClient:
        @staticmethod
        def request(method: str, path: str, query: dict[str, str]) -> dict[str, object]:
            calls.append(
                {
                    "method": method,
                    "path": path,
                    "query": query,
                    "hermes_api_key": os.environ.get("HERMES_TWEET_API_KEY"),
                    "xquik_api_key": os.environ.get("XQUIK_API_KEY"),
                    "base_url": os.environ.get("XQUIK_BASE_URL"),
                }
            )
            return {"items": []}

    monkeypatch.setattr(hermes_tweet_x, "hermes_tweet_client", FakeHermesTweetClient)
    monkeypatch.delenv("HERMES_TWEET_API_KEY", raising=False)
    monkeypatch.delenv("XQUIK_API_KEY", raising=False)
    monkeypatch.delenv("XQUIK_BASE_URL", raising=False)

    response = hermes_tweet_x.search_x(
        {
            "HERMES_TWEET_API_KEY": "xq_test",
            "XQUIK_BASE_URL": "https://example.test",
        },
        "Claude Code skills",
        "2026-05-01",
        "2026-05-23",
        depth="quick",
    )

    assert response == {"items": []}
    assert calls == [
        {
            "method": "GET",
            "path": "/api/v1/x/tweets/search",
            "query": {
                "q": "Claude Code skills",
                "queryType": "Top",
                "sinceTime": "2026-05-01T00:00:00Z",
                "untilTime": "2026-05-23T23:59:59Z",
                "limit": "12",
            },
            "hermes_api_key": "xq_test",
            "xquik_api_key": "xq_test",
            "base_url": "https://example.test",
        }
    ]
    assert os.environ.get("HERMES_TWEET_API_KEY") is None
    assert os.environ.get("XQUIK_API_KEY") is None
    assert os.environ.get("XQUIK_BASE_URL") is None


def test_get_x_source_can_select_hermes_tweet(monkeypatch) -> None:
    monkeypatch.setattr(hermes_tweet_x, "hermes_tweet_client", object())

    assert env.get_x_source({"HERMES_TWEET_API_KEY": "xq_test"}) == "hermes_tweet"
    assert env.get_x_source({"XQUIK_API_KEY": "xq_test"}) == "hermes_tweet"
    assert (
        env.get_x_source(
            {
                "LAST30DAYS_X_BACKEND": "hermes_tweet",
                "HERMES_TWEET_API_KEY": "xq_test",
            }
        )
        == "hermes_tweet"
    )
