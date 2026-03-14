from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from x_scraper.cli import (
    build_search_options,
    cli,
    format_output,
    load_config,
    resolve_token,
    save_config,
    write_output,
)

FAKE_ITEMS = [{"id": "1", "text": "hello"}, {"id": "2", "text": "world"}]


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_scraper():
    with patch("x_scraper.cli.XScraper") as MockXScraper:
        instance = MagicMock()

        for method_name in [
            "search", "execute",
            "get_tweets_by_profile", "get_tweets_by_handle_in_date_range",
            "get_tweets_by_hashtag", "get_tweets_by_keyword",
            "get_tweets_by_keywords", "get_tweets_by_conversation_id",
            "get_tweet_by_url", "get_tweets_by_urls",
            "get_tweets_by_location", "get_tweets_by_multiple_profiles",
            "get_tweets_by_cashtag", "get_tweets_by_mention",
            "get_tweets_with_media_by_handle", "get_tweets_with_images_by_handle",
            "get_tweets_with_videos_by_handle", "get_tweets_with_min_engagement",
            "get_tweets_by_verified_users", "get_tweets_excluding_retweets_by_handle",
            "get_tweets_with_links_by_handle",
        ]:
            setattr(instance, method_name, AsyncMock(return_value=FAKE_ITEMS))

        MockXScraper.return_value = instance
        yield {"cls": MockXScraper, "instance": instance}


# ---------------------------------------------------------------------------
# loadConfig / saveConfig
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_returns_parsed_json_when_file_exists(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text('{"token":"saved-tok"}')

        with patch("x_scraper.cli.CONFIG_FILE", config_file):
            assert load_config() == {"token": "saved-tok"}

    def test_returns_empty_dict_when_file_missing(self, tmp_path):
        with patch("x_scraper.cli.CONFIG_FILE", tmp_path / "nonexistent.json"):
            assert load_config() == {}


class TestSaveConfig:
    def test_creates_directory_and_writes_json(self, tmp_path):
        config_dir = tmp_path / ".x-scraper"
        config_file = config_dir / "config.json"

        with patch("x_scraper.cli.CONFIG_DIR", config_dir), \
             patch("x_scraper.cli.CONFIG_FILE", config_file):
            save_config({"token": "abc"})

        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert data["token"] == "abc"


# ---------------------------------------------------------------------------
# resolveToken
# ---------------------------------------------------------------------------

class TestResolveToken:
    def test_returns_token_from_argument(self):
        assert resolve_token("flag-tok") == "flag-tok"

    def test_returns_token_from_env(self, monkeypatch):
        monkeypatch.setenv("APIFY_TOKEN", "env-tok")
        assert resolve_token(None) == "env-tok"

    def test_returns_token_from_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text('{"token":"file-tok"}')
        with patch("x_scraper.cli.CONFIG_FILE", config_file):
            assert resolve_token(None) == "file-tok"

    def test_exits_when_no_token(self, monkeypatch, tmp_path):
        monkeypatch.delenv("APIFY_TOKEN", raising=False)
        with patch("x_scraper.cli.CONFIG_FILE", tmp_path / "nonexistent.json"):
            with pytest.raises(SystemExit):
                resolve_token(None)


# ---------------------------------------------------------------------------
# formatOutput
# ---------------------------------------------------------------------------

class TestFormatOutput:
    def test_pretty_json_by_default(self):
        items = [{"a": 1}, {"b": 2}]
        assert format_output(items) == json.dumps(items, indent=2)

    def test_compact_json(self):
        items = [{"a": 1}, {"b": 2}]
        assert format_output(items, use_json=True) == json.dumps(items)

    def test_jsonl(self):
        items = [{"a": 1}, {"b": 2}]
        assert format_output(items, use_jsonl=True) == '{"a": 1}\n{"b": 2}'


# ---------------------------------------------------------------------------
# writeOutput
# ---------------------------------------------------------------------------

class TestWriteOutput:
    def test_writes_to_stdout(self, capsys):
        write_output("hello", None)

    def test_writes_to_file(self, tmp_path):
        out_file = tmp_path / "out.json"
        write_output("hello", str(out_file))
        assert out_file.read_text() == "hello\n"


# ---------------------------------------------------------------------------
# buildOptions
# ---------------------------------------------------------------------------

class TestBuildSearchOptions:
    def test_builds_from_params(self):
        opts = build_search_options({"sort": "Latest", "max_items": 50, "lang": "en", "timeout": 60})
        assert opts == {"sort": "Latest", "max_items": 50, "lang": "en", "timeout": 60}

    def test_returns_empty_when_no_flags(self):
        assert build_search_options({}) == {}


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------

class TestInitCommand:
    def test_validates_and_saves_valid_token(self, runner, tmp_path):
        config_dir = tmp_path / ".x-scraper"
        config_file = config_dir / "config.json"

        with patch("x_scraper.cli.CONFIG_DIR", config_dir), \
             patch("x_scraper.cli.CONFIG_FILE", config_file), \
             patch("x_scraper.cli.ApifyClientAsync") as MockApify:
            client = MockApify.return_value
            user_mock = MagicMock()
            user_mock.get = AsyncMock(return_value={"username": "john"})
            client.user = MagicMock(return_value=user_mock)

            result = runner.invoke(cli, ["init"], input="valid-tok\n")

        assert "Authenticated as: john" in result.output
        assert "Token saved" in result.output

    def test_exits_when_no_token_entered(self, runner):
        result = runner.invoke(cli, ["init"], input="\n")
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Convenience commands
# ---------------------------------------------------------------------------

class TestConvenienceCommands:
    def test_profile(self, runner, mock_scraper):
        result = runner.invoke(cli, ["profile", "NASA", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_by_profile.assert_called_once()
        args = mock_scraper["instance"].get_tweets_by_profile.call_args
        assert args[0][0] == "NASA"

    def test_hashtag(self, runner, mock_scraper):
        result = runner.invoke(cli, ["hashtag", "AI", "ML", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_by_hashtag.assert_called_once()

    def test_keyword(self, runner, mock_scraper):
        result = runner.invoke(cli, ["keyword", "artificial intelligence", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_by_keyword.assert_called_once()

    def test_keywords(self, runner, mock_scraper):
        result = runner.invoke(cli, ["keywords", "bitcoin", "ethereum", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_by_keywords.assert_called_once()

    def test_conversation(self, runner, mock_scraper):
        result = runner.invoke(cli, ["conversation", "123456789", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_by_conversation_id.assert_called_once()

    def test_url(self, runner, mock_scraper):
        u = "https://x.com/elonmusk/status/123"
        result = runner.invoke(cli, ["url", u, "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweet_by_url.assert_called_once()

    def test_urls(self, runner, mock_scraper):
        u1 = "https://x.com/a/status/1"
        u2 = "https://x.com/b/status/2"
        result = runner.invoke(cli, ["urls", u1, u2, "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_by_urls.assert_called_once()

    def test_location(self, runner, mock_scraper):
        result = runner.invoke(cli, [
            "location", "coffee", "--token", "tok",
            "--location", "San Francisco", "--radius", "10mi",
        ])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_by_location.assert_called_once()

    def test_profiles(self, runner, mock_scraper):
        result = runner.invoke(cli, ["profiles", "elonmusk", "naval", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_by_multiple_profiles.assert_called_once()

    def test_cashtag(self, runner, mock_scraper):
        result = runner.invoke(cli, ["cashtag", "BTC", "ETH", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_by_cashtag.assert_called_once()

    def test_mention(self, runner, mock_scraper):
        result = runner.invoke(cli, ["mention", "NASA", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_by_mention.assert_called_once()

    def test_media(self, runner, mock_scraper):
        result = runner.invoke(cli, ["media", "NASA", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_with_media_by_handle.assert_called_once()

    def test_images(self, runner, mock_scraper):
        result = runner.invoke(cli, ["images", "NASA", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_with_images_by_handle.assert_called_once()

    def test_videos(self, runner, mock_scraper):
        result = runner.invoke(cli, ["videos", "NASA", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_with_videos_by_handle.assert_called_once()

    def test_engagement(self, runner, mock_scraper):
        result = runner.invoke(cli, [
            "engagement", "bitcoin", "--token", "tok",
            "--min-likes", "1000", "--min-retweets", "100", "--min-replies", "50",
        ])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_with_min_engagement.assert_called_once()

    def test_verified(self, runner, mock_scraper):
        result = runner.invoke(cli, ["verified", "crypto", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_by_verified_users.assert_called_once()

    def test_no_retweets(self, runner, mock_scraper):
        result = runner.invoke(cli, ["no-retweets", "elonmusk", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_excluding_retweets_by_handle.assert_called_once()

    def test_links(self, runner, mock_scraper):
        result = runner.invoke(cli, ["links", "TechCrunch", "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].get_tweets_with_links_by_handle.assert_called_once()


# ---------------------------------------------------------------------------
# Core commands
# ---------------------------------------------------------------------------

class TestCoreCommands:
    def test_search(self, runner, mock_scraper):
        input_json = '{"searchTerms":["from:NASA"]}'
        result = runner.invoke(cli, ["search", "--input", input_json, "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].search.assert_called_once()

    def test_execute(self, runner, mock_scraper):
        input_json = '{"searchTerms":["test"]}'
        result = runner.invoke(cli, ["execute", "--input", input_json, "--token", "tok"])
        assert result.exit_code == 0
        mock_scraper["instance"].execute.assert_called_once()


# ---------------------------------------------------------------------------
# Global options
# ---------------------------------------------------------------------------

class TestGlobalOptions:
    def test_debug_flag(self, runner, mock_scraper):
        result = runner.invoke(cli, ["profile", "NASA", "--token", "tok", "--debug"])
        assert result.exit_code == 0
        mock_scraper["cls"].assert_called_with(token="tok", debug=True)

    def test_json_output(self, runner, mock_scraper):
        result = runner.invoke(cli, ["profile", "NASA", "--token", "tok", "--json"])
        assert result.exit_code == 0
        assert json.dumps(FAKE_ITEMS) in result.output

    def test_jsonl_output(self, runner, mock_scraper):
        result = runner.invoke(cli, ["profile", "NASA", "--token", "tok", "--jsonl"])
        assert result.exit_code == 0

    def test_output_to_file(self, runner, mock_scraper, tmp_path):
        out_file = tmp_path / "tweets.json"
        result = runner.invoke(cli, [
            "profile", "NASA", "--token", "tok", "--output", str(out_file),
        ])
        assert result.exit_code == 0
        assert out_file.exists()

    def test_sort_max_items_lang_timeout_forwarded(self, runner, mock_scraper):
        result = runner.invoke(cli, [
            "profile", "NASA", "--token", "tok",
            "--sort", "Top", "--max-items", "10", "--lang", "en", "--timeout", "30",
        ])
        assert result.exit_code == 0
        call_kwargs = mock_scraper["instance"].get_tweets_by_profile.call_args[1]
        assert call_kwargs["sort"] == "Top"
        assert call_kwargs["max_items"] == 10
        assert call_kwargs["lang"] == "en"
        assert call_kwargs["timeout"] == 30
