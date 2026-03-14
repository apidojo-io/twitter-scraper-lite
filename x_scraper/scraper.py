from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Union

from apify_client import ApifyClientAsync

from .constants import ACTOR_ID, DATASET_PAGE_LIMIT, DEFAULT_TIMEOUT_SECS
from .run_handle import RunHandle

logger = logging.getLogger("x-scraper")


class XScraper:
    """XScraper — the fastest and cheapest way to scrape tweets from X (Twitter).

    Wraps the Apify Twitter Scraper Lite actor with a developer-friendly,
    class-based API. Every method creates a new Apify actor run.

    Example::

        from x_scraper import XScraper

        scraper = XScraper(token="apify_api_xxx")
        tweets = await scraper.get_tweets_by_profile("NASA")
        print(tweets)
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECS,
        debug: bool = False,
    ) -> None:
        """Create a new XScraper instance.

        On initialization, the account subscription is checked in the background.
        If the token belongs to a non-paying (free) account, a warning is logged.

        Args:
            token: Your Apify API token.
            timeout: Default timeout in seconds for sync actor runs.
            debug: Enable debug mode to log internal operations.

        Raises:
            ValueError: If token is not provided.
        """
        if not token:
            raise ValueError(
                'APIFY_TOKEN is required. Pass it as: XScraper(token="apify_api_xxx")'
            )

        self._client = ApifyClientAsync(token=token)
        self._timeout = timeout
        self._debug = debug

        if debug:
            logging.basicConfig(level=logging.DEBUG)

        self._log("Initialized with timeout=%ds debug=%s", self._timeout, self._debug)
        self._check_subscription_background()

    def _log(self, message: str, *args: Any) -> None:
        if not self._debug:
            return
        logger.debug(message, *args)

    def _check_subscription_background(self) -> None:
        """Non-blocking background check of the account's subscription status."""
        self._log("Checking account subscription status...")

        async def _check() -> None:
            try:
                user = await self._client.user().get()
                if user and user.get("isPaying") is False:
                    import warnings
                    warnings.warn(
                        "\n⚠️  [x-scraper] WARNING: This Apify token belongs to a non-paying (free) account.\n"
                        "   The Twitter Scraper actor has limited functionality on free plans (max 10 items, higher pricing).\n"
                        "   Subscribe to a paid plan to unlock full access: https://apify.com/pricing?fpr=yhdrb\n",
                        stacklevel=2,
                    )
                else:
                    self._log("Account is on a paid plan.")
            except Exception:
                self._log("Could not verify subscription status (will fail on run if token is invalid).")

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_check())
        except RuntimeError:
            pass

    def _build_input(self, input_data: dict, options: dict | None = None) -> dict:
        """Build the final actor input by merging user options. Always injects ``python: True``."""
        options = options or {}
        merged = {**input_data, "python": True}

        if "sort" in options:
            merged["sort"] = options["sort"]
        if "max_items" in options:
            merged["maxItems"] = options["max_items"]
        if "lang" in options:
            merged["tweetLanguage"] = options["lang"]

        return merged

    async def _fetch_all_items(self, dataset_id: str) -> list[dict]:
        """Auto-paginate all items from a dataset."""
        all_items: list[dict] = []
        offset = 0
        page = 0

        while True:
            result = await self._client.dataset(dataset_id).list_items(
                offset=offset, limit=DATASET_PAGE_LIMIT, clean=True
            )
            items = result.items

            page += 1
            all_items.extend(items)
            self._log(
                "fetch_all_items() page=%d fetched=%d total_so_far=%d",
                page, len(items), len(all_items),
            )

            if len(items) < DATASET_PAGE_LIMIT:
                break
            offset += len(items)

        return all_items

    # -------------------------------------------------------------------------
    # CORE METHODS
    # -------------------------------------------------------------------------

    async def execute(
        self,
        input_data: dict,
        *,
        timeout: int | None = None,
        full_response: bool = False,
    ) -> Union[list[dict], dict]:
        """Execute the Twitter scraper with a raw actor input object.

        This is the "I know what I'm doing" escape hatch — pass any valid actor
        input and get items back. ``python: True`` is still injected automatically.

        Args:
            input_data: Raw actor input (searchTerms, startUrls, twitterHandles, etc.).
            timeout: Timeout in seconds (overrides constructor default).
            full_response: If True, returns ``{"items", "run_id", "dataset_id"}``.

        Returns:
            Tweet items list, or full response dict.
        """
        final_input = {**input_data, "python": True}
        timeout = timeout if timeout is not None else self._timeout

        self._log("execute() input=%s timeout=%ds", final_input, timeout)

        run = await self._client.actor(ACTOR_ID).call(
            run_input=final_input, timeout_secs=timeout
        )

        self._log(
            "execute() run started id=%s status=%s dataset_id=%s",
            run["id"], run["status"], run["defaultDatasetId"],
        )

        items = await self._fetch_all_items(run["defaultDatasetId"])

        self._log("execute() completed total_items=%d", len(items))

        if full_response:
            return {"items": items, "run_id": run["id"], "dataset_id": run["defaultDatasetId"]}

        return items

    async def search(
        self,
        input_data: dict,
        *,
        sort: str | None = None,
        max_items: int | None = None,
        lang: str | None = None,
        timeout: int | None = None,
        full_response: bool = False,
    ) -> Union[list[dict], dict]:
        """Run the Twitter scraper synchronously — waits for the run to finish and
        returns all dataset items. Auto-paginates through the full dataset.

        Args:
            input_data: Actor input (searchTerms, startUrls, etc.).
            sort: Sort order: 'Latest', 'Top', or 'Latest + Top'.
            max_items: Maximum number of tweet items to return.
            lang: Restrict tweets to this language (ISO 639-1 code).
            timeout: Timeout in seconds (overrides constructor default).
            full_response: If True, returns ``{"items", "run_id", "dataset_id"}``.

        Returns:
            Tweet items list, or full response dict.
        """
        options = {}
        if sort is not None:
            options["sort"] = sort
        if max_items is not None:
            options["max_items"] = max_items
        if lang is not None:
            options["lang"] = lang

        final_input = self._build_input(input_data, options)
        timeout = timeout if timeout is not None else self._timeout

        self._log("search() input=%s timeout=%ds", final_input, timeout)

        run = await self._client.actor(ACTOR_ID).call(
            run_input=final_input, timeout_secs=timeout
        )

        self._log(
            "search() run started id=%s status=%s dataset_id=%s",
            run["id"], run["status"], run["defaultDatasetId"],
        )

        items = await self._fetch_all_items(run["defaultDatasetId"])

        self._log("search() completed total_items=%d", len(items))

        if full_response:
            return {"items": items, "run_id": run["id"], "dataset_id": run["defaultDatasetId"]}

        return items

    async def search_async(
        self,
        input_data: dict,
        *,
        sort: str | None = None,
        max_items: int | None = None,
        lang: str | None = None,
    ) -> RunHandle:
        """Start the Twitter scraper asynchronously without waiting for completion.

        Returns a :class:`RunHandle` that you can poll and fetch results from.

        Args:
            input_data: Actor input (searchTerms, startUrls, etc.).
            sort: Sort order.
            max_items: Maximum number of items.
            lang: Language filter.

        Returns:
            A RunHandle for the started run.
        """
        options = {}
        if sort is not None:
            options["sort"] = sort
        if max_items is not None:
            options["max_items"] = max_items
        if lang is not None:
            options["lang"] = lang

        final_input = self._build_input(input_data, options)

        self._log("search_async() input=%s", final_input)

        run_data = await self._client.actor(ACTOR_ID).start(run_input=final_input)

        self._log("search_async() run started id=%s status=%s", run_data["id"], run_data["status"])

        return RunHandle(run_data, self._client)

    async def stream(
        self,
        input_data: dict,
        *,
        sort: str | None = None,
        max_items: int | None = None,
        lang: str | None = None,
        timeout: int | None = None,
    ) -> AsyncIterator[dict]:
        """Run the Twitter scraper and stream results as an async iterator.

        Yields tweet items one by one, auto-paginating through the dataset.

        Args:
            input_data: Actor input (searchTerms, startUrls, etc.).
            sort: Sort order.
            max_items: Maximum number of items.
            lang: Language filter.
            timeout: Timeout in seconds.

        Yields:
            A single tweet item dict.
        """
        options = {}
        if sort is not None:
            options["sort"] = sort
        if max_items is not None:
            options["max_items"] = max_items
        if lang is not None:
            options["lang"] = lang

        final_input = self._build_input(input_data, options)
        timeout = timeout if timeout is not None else self._timeout

        self._log("stream() input=%s timeout=%ds", final_input, timeout)

        run = await self._client.actor(ACTOR_ID).call(
            run_input=final_input, timeout_secs=timeout
        )

        self._log("stream() run completed id=%s, fetching dataset pages...", run["id"])

        offset = 0
        page = 0
        total = 0

        while True:
            result = await self._client.dataset(run["defaultDatasetId"]).list_items(
                offset=offset, limit=DATASET_PAGE_LIMIT, clean=True
            )
            items = result.items

            page += 1
            total += len(items)
            self._log("stream() page=%d fetched=%d total_so_far=%d", page, len(items), total)

            for item in items:
                yield item

            if len(items) < DATASET_PAGE_LIMIT:
                break
            offset += len(items)

        self._log("stream() done total_yielded=%d", total)

    # -------------------------------------------------------------------------
    # CONVENIENCE METHODS
    # -------------------------------------------------------------------------

    async def get_tweets_by_profile(self, handle: str, **options: Any) -> Union[list[dict], dict]:
        """Fetch tweets posted by a specific Twitter/X profile.

        Args:
            handle: Twitter handle without the @ prefix (e.g. 'NASA').
            **options: Keyword arguments forwarded to :meth:`search`
                (sort, max_items, lang, timeout, full_response).

        Returns:
            Tweet items list, or full response dict.
        """
        return await self.search({"searchTerms": [f"from:{handle}"]}, **options)

    async def get_tweets_by_handle_in_date_range(
        self, handle: str, since: str, until: str, **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch tweets from a specific handle within a date range.

        Args:
            handle: Twitter handle without the @ prefix.
            since: Start date in YYYY-MM-DD format.
            until: End date in YYYY-MM-DD format.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search(
            {"searchTerms": [f"from:{handle} since:{since} until:{until}"]}, **options
        )

    async def get_tweets_by_hashtag(
        self, hashtags: str | list[str], **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch tweets containing specific hashtags.

        Args:
            hashtags: One or more hashtags. The '#' prefix is added automatically if missing.
            **options: Forwarded to :meth:`search`.
        """
        tags = hashtags if isinstance(hashtags, list) else [hashtags]
        query = " ".join(t if t.startswith("#") else f"#{t}" for t in tags)
        return await self.search({"searchTerms": [query]}, **options)

    async def get_tweets_by_keyword(self, keyword: str, **options: Any) -> Union[list[dict], dict]:
        """Search tweets by a single keyword or phrase.

        Args:
            keyword: The keyword or phrase to search for.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search({"searchTerms": [keyword]}, **options)

    async def search_tweets(self, keyword: str, **options: Any) -> Union[list[dict], dict]:
        """Alias for :meth:`get_tweets_by_keyword`."""
        return await self.get_tweets_by_keyword(keyword, **options)

    async def get_tweets_by_keywords(
        self, keywords: list[str], **options: Any
    ) -> Union[list[dict], dict]:
        """Search tweets by multiple keywords, joined with OR.

        Args:
            keywords: Array of keywords to search for.
            **options: Forwarded to :meth:`search`.
        """
        query = " OR ".join(keywords)
        return await self.search({"searchTerms": [query]}, **options)

    async def search_tweets_by_multiple_keywords(
        self, keywords: list[str], **options: Any
    ) -> Union[list[dict], dict]:
        """Alias for :meth:`get_tweets_by_keywords`."""
        return await self.get_tweets_by_keywords(keywords, **options)

    async def get_tweets_by_conversation_id(
        self, conversation_id: str, **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch replies/tweets from a conversation thread by its conversation ID.

        Args:
            conversation_id: The tweet ID that started the conversation thread.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search(
            {"searchTerms": [f"conversation_id:{conversation_id}"]}, **options
        )

    async def get_tweet_by_url(self, tweet_url: str, **options: Any) -> Union[list[dict], dict]:
        """Fetch a single tweet by its URL.

        Args:
            tweet_url: Full URL of the tweet.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search({"startUrls": [tweet_url]}, **options)

    async def get_tweets_by_urls(
        self, urls: list[str], **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch tweets from multiple URLs.

        Args:
            urls: Array of Twitter/X URLs.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search({"startUrls": urls}, **options)

    async def get_tweets_by_location(
        self, query: str, location: str, radius: str, **options: Any
    ) -> Union[list[dict], dict]:
        """Search tweets near a geographic location.

        Args:
            query: Search query or keyword.
            location: Location name (e.g. 'San Francisco').
            radius: Search radius with unit (e.g. '10mi', '25km').
            **options: Forwarded to :meth:`search`.
        """
        return await self.search(
            {"searchTerms": [f'{query} near:"{location}" within:{radius}']}, **options
        )

    async def get_tweets_by_multiple_profiles(
        self, handles: list[str], **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch tweets from multiple Twitter/X profiles in a single run.

        Args:
            handles: Array of Twitter handles without the @ prefix.
            **options: Forwarded to :meth:`search`.
        """
        search_terms = [f"from:{h}" for h in handles]
        return await self.search({"searchTerms": search_terms}, **options)

    async def get_tweets_by_cashtag(
        self, cashtags: str | list[str], **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch tweets containing specific cashtags (e.g. $BTC, $AAPL).

        Args:
            cashtags: One or more cashtags. The '$' prefix is added automatically if missing.
            **options: Forwarded to :meth:`search`.
        """
        tags = cashtags if isinstance(cashtags, list) else [cashtags]
        query = " OR ".join(t if t.startswith("$") else f"${t}" for t in tags)
        return await self.search({"searchTerms": [query]}, **options)

    async def get_tweets_by_mention(self, handle: str, **options: Any) -> Union[list[dict], dict]:
        """Fetch tweets that mention a specific user.

        Args:
            handle: Twitter handle without the @ prefix.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search({"searchTerms": [f"@{handle}"]}, **options)

    async def get_tweets_with_media_by_handle(
        self, handle: str, **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch tweets with media (images or videos) from a specific handle.

        Args:
            handle: Twitter handle without the @ prefix.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search(
            {"searchTerms": [f"from:{handle} filter:media"]}, **options
        )

    async def get_tweets_with_images_by_handle(
        self, handle: str, **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch tweets with images from a specific handle.

        Args:
            handle: Twitter handle without the @ prefix.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search(
            {"searchTerms": [f"from:{handle} filter:images"]}, **options
        )

    async def get_tweets_with_videos_by_handle(
        self, handle: str, **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch tweets with videos from a specific handle.

        Args:
            handle: Twitter handle without the @ prefix.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search(
            {"searchTerms": [f"from:{handle} filter:videos"]}, **options
        )

    async def get_tweets_with_min_engagement(
        self,
        query: str,
        *,
        min_likes: int | None = None,
        min_retweets: int | None = None,
        min_replies: int | None = None,
        **options: Any,
    ) -> Union[list[dict], dict]:
        """Fetch tweets matching a query with minimum engagement thresholds.

        Args:
            query: Search query or keyword.
            min_likes: Minimum number of likes (favorites).
            min_retweets: Minimum number of retweets.
            min_replies: Minimum number of replies.
            **options: Forwarded to :meth:`search` (sort, max_items, lang, timeout, full_response).
        """
        parts = [query]
        if min_likes is not None:
            parts.append(f"min_faves:{min_likes}")
        if min_retweets is not None:
            parts.append(f"min_retweets:{min_retweets}")
        if min_replies is not None:
            parts.append(f"min_replies:{min_replies}")
        return await self.search({"searchTerms": [" ".join(parts)]}, **options)

    async def get_tweets_by_verified_users(
        self, query: str, **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch tweets from verified users only, matching a query.

        Args:
            query: Search query or keyword.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search(
            {"searchTerms": [f"{query} filter:verified"]}, **options
        )

    async def get_tweets_excluding_retweets_by_handle(
        self, handle: str, **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch tweets from a specific handle, excluding retweets.

        Args:
            handle: Twitter handle without the @ prefix.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search(
            {"searchTerms": [f"from:{handle} -filter:retweets"]}, **options
        )

    async def get_tweets_with_links_by_handle(
        self, handle: str, **options: Any
    ) -> Union[list[dict], dict]:
        """Fetch tweets containing links from a specific handle.

        Args:
            handle: Twitter handle without the @ prefix.
            **options: Forwarded to :meth:`search`.
        """
        return await self.search(
            {"searchTerms": [f"from:{handle} filter:links"]}, **options
        )
