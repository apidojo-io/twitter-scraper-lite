from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from x_scraper import RunHandle, XScraper
from x_scraper.constants import ACTOR_ID

FAKE_RUN = {
    "id": "run-123",
    "defaultDatasetId": "dataset-456",
    "status": "SUCCEEDED",
}

FAKE_TWEETS = [
    {"type": "tweet", "id": "1", "text": "Hello world", "author": {"userName": "test"}},
    {"type": "tweet", "id": "2", "text": "Another tweet", "author": {"userName": "test2"}},
]


class FakeListResult:
    def __init__(self, items):
        self.items = items


@pytest.fixture
def mock_client():
    with patch("x_scraper.scraper.ApifyClientAsync") as MockClient:
        client = MockClient.return_value

        call_mock = AsyncMock(return_value=FAKE_RUN)
        start_mock = AsyncMock(return_value=FAKE_RUN)
        actor_mock = MagicMock()
        actor_mock.call = call_mock
        actor_mock.start = start_mock
        client.actor = MagicMock(return_value=actor_mock)

        list_items_mock = AsyncMock(return_value=FakeListResult(FAKE_TWEETS))
        dataset_mock = MagicMock()
        dataset_mock.list_items = list_items_mock
        client.dataset = MagicMock(return_value=dataset_mock)

        wait_for_finish_mock = AsyncMock(return_value=FAKE_RUN)
        run_mock = MagicMock()
        run_mock.wait_for_finish = wait_for_finish_mock
        client.run = MagicMock(return_value=run_mock)

        user_get_mock = AsyncMock(return_value={"isPaying": True})
        user_mock = MagicMock()
        user_mock.get = user_get_mock
        client.user = MagicMock(return_value=user_mock)

        yield {
            "client": client,
            "actor_mock": client.actor,
            "call_mock": call_mock,
            "start_mock": start_mock,
            "dataset_mock": client.dataset,
            "list_items_mock": list_items_mock,
            "run_mock": client.run,
            "wait_for_finish_mock": wait_for_finish_mock,
            "user_get_mock": user_get_mock,
        }


def make_scraper(**kwargs):
    return XScraper(token="test-token", **kwargs)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_throws_when_token_is_missing(self, mock_client):
        with pytest.raises(ValueError, match="APIFY_TOKEN is required"):
            XScraper(token="")

    def test_throws_when_called_with_no_arguments(self, mock_client):
        with pytest.raises(ValueError, match="APIFY_TOKEN is required"):
            XScraper()

    def test_creates_instance_with_valid_token(self, mock_client):
        scraper = XScraper(token="abc")
        assert scraper is not None


# ---------------------------------------------------------------------------
# Core: execute
# ---------------------------------------------------------------------------

class TestExecute:
    @pytest.mark.asyncio
    async def test_passes_raw_input_and_injects_python(self, mock_client):
        scraper = make_scraper()
        input_data = {"searchTerms": ["custom query"], "sort": "Top", "maxItems": 10}
        result = await scraper.execute(input_data)

        mock_client["actor_mock"].assert_called_with(ACTOR_ID)
        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input == {**input_data, "python": True}
        assert result == FAKE_TWEETS

    @pytest.mark.asyncio
    async def test_returns_full_response_when_requested(self, mock_client):
        scraper = make_scraper()
        result = await scraper.execute({"searchTerms": ["test"]}, full_response=True)

        assert result == {
            "items": FAKE_TWEETS,
            "run_id": "run-123",
            "dataset_id": "dataset-456",
        }

    @pytest.mark.asyncio
    async def test_does_not_merge_options_into_input(self, mock_client):
        scraper = make_scraper()
        await scraper.execute({"searchTerms": ["raw"]})

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input == {"searchTerms": ["raw"], "python": True}


# ---------------------------------------------------------------------------
# Core: search
# ---------------------------------------------------------------------------

class TestSearch:
    @pytest.mark.asyncio
    async def test_calls_actor_with_merged_input_and_python(self, mock_client):
        scraper = make_scraper()
        result = await scraper.search(
            {"searchTerms": ["from:NASA"]}, sort="Latest", max_items=50
        )

        mock_client["actor_mock"].assert_called_with(ACTOR_ID)
        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input == {
            "searchTerms": ["from:NASA"],
            "sort": "Latest",
            "maxItems": 50,
            "python": True,
        }
        assert result == FAKE_TWEETS

    @pytest.mark.asyncio
    async def test_merges_lang_option_as_tweet_language(self, mock_client):
        scraper = make_scraper()
        await scraper.search({"searchTerms": ["test"]}, lang="en")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["tweetLanguage"] == "en"

    @pytest.mark.asyncio
    async def test_uses_custom_timeout(self, mock_client):
        scraper = make_scraper()
        await scraper.search({"searchTerms": ["test"]}, timeout=60)

        assert mock_client["call_mock"].call_args[1]["timeout_secs"] == 60

    @pytest.mark.asyncio
    async def test_returns_full_response_when_requested(self, mock_client):
        scraper = make_scraper()
        result = await scraper.search(
            {"searchTerms": ["test"]}, full_response=True
        )

        assert result["items"] == FAKE_TWEETS
        assert result["run_id"] == "run-123"
        assert result["dataset_id"] == "dataset-456"

    @pytest.mark.asyncio
    async def test_auto_paginates(self, mock_client):
        page1 = [{"id": f"p1-{i}"} for i in range(10000)]
        page2 = [{"id": "p2-0"}, {"id": "p2-1"}]

        mock_client["list_items_mock"].side_effect = [
            FakeListResult(page1),
            FakeListResult(page2),
        ]

        scraper = make_scraper()
        result = await scraper.search({"searchTerms": ["big"]})

        assert mock_client["list_items_mock"].call_count == 2
        assert len(result) == 10002


# ---------------------------------------------------------------------------
# Core: search_async
# ---------------------------------------------------------------------------

class TestSearchAsync:
    @pytest.mark.asyncio
    async def test_starts_actor_and_returns_run_handle(self, mock_client):
        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["from:NASA"]})

        mock_client["actor_mock"].assert_called_with(ACTOR_ID)
        called_input = mock_client["start_mock"].call_args[1]["run_input"]
        assert called_input["python"] is True
        assert called_input["searchTerms"] == ["from:NASA"]
        assert isinstance(handle, RunHandle)
        assert handle.run_id == "run-123"
        assert handle.dataset_id == "dataset-456"
        assert handle.status == "SUCCEEDED"


# ---------------------------------------------------------------------------
# Core: stream
# ---------------------------------------------------------------------------

class TestStream:
    @pytest.mark.asyncio
    async def test_yields_items_one_by_one(self, mock_client):
        scraper = make_scraper()
        collected = []
        async for tweet in scraper.stream({"searchTerms": ["from:NASA"]}):
            collected.append(tweet)

        assert collected == FAKE_TWEETS
        assert mock_client["call_mock"].called

    @pytest.mark.asyncio
    async def test_auto_paginates_through_multiple_pages(self, mock_client):
        page1 = [{"id": f"p1-{i}"} for i in range(10000)]
        page2 = [{"id": "p2-0"}]

        mock_client["list_items_mock"].side_effect = [
            FakeListResult(page1),
            FakeListResult(page2),
        ]

        scraper = make_scraper()
        collected = []
        async for tweet in scraper.stream({"searchTerms": ["big"]}):
            collected.append(tweet)

        assert mock_client["list_items_mock"].call_count == 2
        assert len(collected) == 10001


# ---------------------------------------------------------------------------
# python injection
# ---------------------------------------------------------------------------

class TestClawhubInjection:
    @pytest.mark.asyncio
    async def test_included_in_search(self, mock_client):
        scraper = make_scraper()
        await scraper.search({"searchTerms": ["test"]})
        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["python"] is True

    @pytest.mark.asyncio
    async def test_included_in_execute(self, mock_client):
        scraper = make_scraper()
        await scraper.execute({"searchTerms": ["test"]})
        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["python"] is True

    @pytest.mark.asyncio
    async def test_included_in_search_async(self, mock_client):
        scraper = make_scraper()
        await scraper.search_async({"searchTerms": ["test"]})
        called_input = mock_client["start_mock"].call_args[1]["run_input"]
        assert called_input["python"] is True


# ---------------------------------------------------------------------------
# Convenience methods: input construction
# ---------------------------------------------------------------------------

class TestGetTweetsByProfile:
    @pytest.mark.asyncio
    async def test_builds_from_handle_search_term(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_profile("NASA", sort="Latest")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["from:NASA"]
        assert called_input["sort"] == "Latest"
        assert called_input["python"] is True


class TestGetTweetsByHandleInDateRange:
    @pytest.mark.asyncio
    async def test_builds_date_range_query(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_handle_in_date_range("NASA", "2024-01-01", "2024-06-01")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == [
            "from:NASA since:2024-01-01 until:2024-06-01"
        ]


class TestGetTweetsByHashtag:
    @pytest.mark.asyncio
    async def test_builds_hashtag_query_from_list(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_hashtag(["AI", "MachineLearning"])

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["#AI #MachineLearning"]

    @pytest.mark.asyncio
    async def test_accepts_single_string(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_hashtag("AI")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["#AI"]

    @pytest.mark.asyncio
    async def test_does_not_double_prefix(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_hashtag("#AI")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["#AI"]


class TestGetTweetsByKeyword:
    @pytest.mark.asyncio
    async def test_passes_keyword_as_search_term(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_keyword("artificial intelligence", lang="en")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["artificial intelligence"]
        assert called_input["tweetLanguage"] == "en"
        assert called_input["python"] is True


class TestSearchTweets:
    @pytest.mark.asyncio
    async def test_is_alias_for_get_tweets_by_keyword(self, mock_client):
        scraper = make_scraper()
        await scraper.search_tweets("AI", sort="Latest")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["AI"]


class TestGetTweetsByKeywords:
    @pytest.mark.asyncio
    async def test_joins_keywords_with_or(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_keywords(["bitcoin", "ethereum", "solana"])

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["bitcoin OR ethereum OR solana"]


class TestSearchTweetsByMultipleKeywords:
    @pytest.mark.asyncio
    async def test_is_alias_for_get_tweets_by_keywords(self, mock_client):
        scraper = make_scraper()
        await scraper.search_tweets_by_multiple_keywords(["AI", "ML"])

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["AI OR ML"]


class TestGetTweetsByConversationId:
    @pytest.mark.asyncio
    async def test_builds_conversation_id_query(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_conversation_id("1728108619189874825")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["conversation_id:1728108619189874825"]


class TestGetTweetByUrl:
    @pytest.mark.asyncio
    async def test_passes_url_as_start_urls(self, mock_client):
        url = "https://x.com/elonmusk/status/1728108619189874825"
        scraper = make_scraper()
        await scraper.get_tweet_by_url(url)

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["startUrls"] == [url]


class TestGetTweetsByUrls:
    @pytest.mark.asyncio
    async def test_passes_multiple_urls(self, mock_client):
        urls = [
            "https://x.com/elonmusk/status/123",
            "https://twitter.com/i/lists/456",
        ]
        scraper = make_scraper()
        await scraper.get_tweets_by_urls(urls)

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["startUrls"] == urls


class TestGetTweetsByLocation:
    @pytest.mark.asyncio
    async def test_builds_near_within_query(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_location("coffee", "San Francisco", "10mi")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ['coffee near:"San Francisco" within:10mi']


class TestGetTweetsByMultipleProfiles:
    @pytest.mark.asyncio
    async def test_builds_from_for_each_handle(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_multiple_profiles(["elonmusk", "naval", "paulg"])

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == [
            "from:elonmusk",
            "from:naval",
            "from:paulg",
        ]


class TestGetTweetsByCashtag:
    @pytest.mark.asyncio
    async def test_joins_cashtags_with_or(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_cashtag(["BTC", "ETH", "SOL"])

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["$BTC OR $ETH OR $SOL"]

    @pytest.mark.asyncio
    async def test_does_not_double_prefix(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_cashtag(["$BTC", "ETH"])

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["$BTC OR $ETH"]

    @pytest.mark.asyncio
    async def test_accepts_single_string(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_cashtag("AAPL")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["$AAPL"]


class TestGetTweetsByMention:
    @pytest.mark.asyncio
    async def test_builds_at_handle_query(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_mention("NASA")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["@NASA"]


class TestGetTweetsWithMediaByHandle:
    @pytest.mark.asyncio
    async def test_builds_filter_media(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_with_media_by_handle("NASA")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["from:NASA filter:media"]


class TestGetTweetsWithImagesByHandle:
    @pytest.mark.asyncio
    async def test_builds_filter_images(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_with_images_by_handle("NASA")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["from:NASA filter:images"]


class TestGetTweetsWithVideosByHandle:
    @pytest.mark.asyncio
    async def test_builds_filter_videos(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_with_videos_by_handle("NASA")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["from:NASA filter:videos"]


class TestGetTweetsWithMinEngagement:
    @pytest.mark.asyncio
    async def test_builds_min_faves_and_min_retweets(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_with_min_engagement(
            "bitcoin", min_likes=1000, min_retweets=100, sort="Top"
        )

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == [
            "bitcoin min_faves:1000 min_retweets:100"
        ]
        assert called_input["sort"] == "Top"

    @pytest.mark.asyncio
    async def test_builds_min_replies(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_with_min_engagement("test", min_replies=50)

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["test min_replies:50"]


class TestGetTweetsByVerifiedUsers:
    @pytest.mark.asyncio
    async def test_builds_filter_verified(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_by_verified_users("cryptocurrency")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["cryptocurrency filter:verified"]


class TestGetTweetsExcludingRetweetsByHandle:
    @pytest.mark.asyncio
    async def test_builds_negative_filter_retweets(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_excluding_retweets_by_handle("elonmusk")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["from:elonmusk -filter:retweets"]


class TestGetTweetsWithLinksByHandle:
    @pytest.mark.asyncio
    async def test_builds_filter_links(self, mock_client):
        scraper = make_scraper()
        await scraper.get_tweets_with_links_by_handle("TechCrunch")

        called_input = mock_client["call_mock"].call_args[1]["run_input"]
        assert called_input["searchTerms"] == ["from:TechCrunch filter:links"]


# ---------------------------------------------------------------------------
# RunHandle
# ---------------------------------------------------------------------------

class TestRunHandle:
    @pytest.mark.asyncio
    async def test_wait_for_finish_resolves_on_succeeded(self, mock_client):
        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})
        result = await handle.wait_for_finish()

        mock_client["run_mock"].assert_called_with("run-123")
        assert mock_client["wait_for_finish_mock"].called
        assert result is handle

    @pytest.mark.asyncio
    async def test_wait_for_finish_throws_on_failed(self, mock_client):
        mock_client["wait_for_finish_mock"].return_value = {**FAKE_RUN, "status": "FAILED"}

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})

        with pytest.raises(RuntimeError, match="Run run-123 finished with status: FAILED"):
            await handle.wait_for_finish()

    @pytest.mark.asyncio
    async def test_get_items_fetches_dataset(self, mock_client):
        mock_client["wait_for_finish_mock"].return_value = FAKE_RUN

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})
        await handle.wait_for_finish()
        items = await handle.get_items()

        assert items == FAKE_TWEETS
        mock_client["dataset_mock"].assert_called_with("dataset-456")

    @pytest.mark.asyncio
    async def test_get_items_with_full_response(self, mock_client):
        mock_client["wait_for_finish_mock"].return_value = FAKE_RUN

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})
        await handle.wait_for_finish()
        result = await handle.get_items(full_response=True)

        assert result["items"] == FAKE_TWEETS
        assert result["run_id"] == "run-123"
        assert result["dataset_id"] == "dataset-456"

    @pytest.mark.asyncio
    async def test_stream_yields_items(self, mock_client):
        mock_client["wait_for_finish_mock"].return_value = FAKE_RUN

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})
        await handle.wait_for_finish()

        collected = []
        async for tweet in handle.stream():
            collected.append(tweet)

        assert collected == FAKE_TWEETS

    @pytest.mark.asyncio
    async def test_wait_for_finish_polls_multiple_times(self, mock_client):
        mock_client["wait_for_finish_mock"].side_effect = [
            {**FAKE_RUN, "status": "RUNNING"},
            FAKE_RUN,
        ]

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})
        result = await handle.wait_for_finish()

        assert mock_client["wait_for_finish_mock"].call_count == 2
        assert result is handle

    @pytest.mark.asyncio
    async def test_wait_for_finish_throws_on_timeout(self, mock_client):
        mock_client["wait_for_finish_mock"].return_value = {**FAKE_RUN, "status": "RUNNING"}

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})

        with pytest.raises(TimeoutError, match="did not finish within 0s"):
            await handle.wait_for_finish(wait_secs=0)

    @pytest.mark.asyncio
    async def test_get_items_auto_waits(self, mock_client):
        mock_client["start_mock"].return_value = {**FAKE_RUN, "status": "RUNNING"}
        mock_client["wait_for_finish_mock"].return_value = FAKE_RUN

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})
        items = await handle.get_items()

        assert mock_client["wait_for_finish_mock"].called
        assert items == FAKE_TWEETS

    @pytest.mark.asyncio
    async def test_get_items_throws_on_non_succeeded_terminal(self, mock_client):
        mock_client["start_mock"].return_value = {**FAKE_RUN, "status": "FAILED"}

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})

        with pytest.raises(RuntimeError, match="Run run-123 finished with status: FAILED"):
            await handle.get_items()

    @pytest.mark.asyncio
    async def test_get_items_auto_paginates(self, mock_client):
        page1 = [{"id": f"p1-{i}"} for i in range(10000)]
        page2 = [{"id": "p2-0"}]

        mock_client["list_items_mock"].side_effect = [
            FakeListResult(page1),
            FakeListResult(page2),
        ]

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})
        await handle.wait_for_finish()
        items = await handle.get_items()

        assert mock_client["list_items_mock"].call_count == 2
        assert len(items) == 10001

    @pytest.mark.asyncio
    async def test_stream_auto_waits(self, mock_client):
        mock_client["start_mock"].return_value = {**FAKE_RUN, "status": "RUNNING"}
        mock_client["wait_for_finish_mock"].return_value = FAKE_RUN

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})

        collected = []
        async for tweet in handle.stream():
            collected.append(tweet)

        assert mock_client["wait_for_finish_mock"].called
        assert collected == FAKE_TWEETS

    @pytest.mark.asyncio
    async def test_stream_throws_on_non_succeeded_terminal(self, mock_client):
        mock_client["start_mock"].return_value = {**FAKE_RUN, "status": "FAILED"}

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})

        with pytest.raises(RuntimeError, match="Run run-123 finished with status: FAILED"):
            async for _ in handle.stream():
                pass

    @pytest.mark.asyncio
    async def test_stream_auto_paginates(self, mock_client):
        page1 = [{"id": f"p1-{i}"} for i in range(10000)]
        page2 = [{"id": "p2-0"}]

        mock_client["list_items_mock"].side_effect = [
            FakeListResult(page1),
            FakeListResult(page2),
        ]

        scraper = make_scraper()
        handle = await scraper.search_async({"searchTerms": ["test"]})
        await handle.wait_for_finish()

        collected = []
        async for tweet in handle.stream():
            collected.append(tweet)

        assert mock_client["list_items_mock"].call_count == 2
        assert len(collected) == 10001


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------

class TestErrorPropagation:
    @pytest.mark.asyncio
    async def test_propagates_actor_call_errors(self, mock_client):
        mock_client["call_mock"].side_effect = Exception("401 Unauthorized")

        scraper = make_scraper()
        with pytest.raises(Exception, match="401 Unauthorized"):
            await scraper.search({"searchTerms": ["test"]})

    @pytest.mark.asyncio
    async def test_propagates_actor_start_errors(self, mock_client):
        mock_client["start_mock"].side_effect = Exception("Rate limit exceeded")

        scraper = make_scraper()
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await scraper.search_async({"searchTerms": ["test"]})

    @pytest.mark.asyncio
    async def test_propagates_dataset_fetch_errors(self, mock_client):
        mock_client["list_items_mock"].side_effect = Exception("Dataset not found")

        scraper = make_scraper()
        with pytest.raises(Exception, match="Dataset not found"):
            await scraper.search({"searchTerms": ["test"]})
