"""Manual test script for x-scraper.

Usage:
    1. pip install -e .
    2. APIFY_TOKEN=apify_api_xxx python test_manual.py

Set the APIFY_TOKEN environment variable before running.
Uncomment whichever section you want to test.
"""

import asyncio
import os
import sys

from x_scraper import XScraper

TOKEN = os.environ.get("APIFY_TOKEN")

if not TOKEN:
    print("Missing APIFY_TOKEN. Run as: APIFY_TOKEN=apify_api_xxx python test_manual.py", file=sys.stderr)
    sys.exit(1)

scraper = XScraper(token=TOKEN, debug=False)


async def main():
    # ── Pick a test by uncommenting one of the sections below ──

    # 1. get_tweets_by_profile
    tweets = await scraper.get_tweets_by_profile("NASA", sort="Latest", max_items=5)
    print("get_tweets_by_profile:", tweets)

    # 2. get_tweets_by_handle_in_date_range
    # tweets = await scraper.get_tweets_by_handle_in_date_range("NASA", "2024-01-01", "2024-06-01", sort="Latest", max_items=5)
    # print("get_tweets_by_handle_in_date_range:", tweets)

    # 3. get_tweets_by_keyword
    # tweets = await scraper.get_tweets_by_keyword("artificial intelligence", lang="en", sort="Latest", max_items=5)
    # print("get_tweets_by_keyword:", tweets)

    # 4. search_tweets (alias for get_tweets_by_keyword)
    # tweets = await scraper.search_tweets("artificial intelligence", max_items=5)
    # print("search_tweets:", tweets)

    # 5. get_tweets_by_keywords (multiple keywords joined with OR)
    # tweets = await scraper.get_tweets_by_keywords(["bitcoin", "ethereum", "solana"], lang="en", max_items=5)
    # print("get_tweets_by_keywords:", tweets)

    # 6. search_tweets_by_multiple_keywords (alias for get_tweets_by_keywords)
    # tweets = await scraper.search_tweets_by_multiple_keywords(["AI", "ML"], max_items=5)
    # print("search_tweets_by_multiple_keywords:", tweets)

    # 7. get_tweets_by_hashtag
    # tweets = await scraper.get_tweets_by_hashtag(["AI", "MachineLearning"], sort="Latest", max_items=5)
    # print("get_tweets_by_hashtag:", tweets)

    # 8. get_tweets_by_conversation_id
    # tweets = await scraper.get_tweets_by_conversation_id("1728108619189874825", sort="Latest", max_items=5)
    # print("get_tweets_by_conversation_id:", tweets)

    # 9. get_tweet_by_url
    # tweets = await scraper.get_tweet_by_url("https://x.com/elonmusk/status/1728108619189874825")
    # print("get_tweet_by_url:", tweets)

    # 10. get_tweets_by_urls
    # tweets = await scraper.get_tweets_by_urls([
    #     "https://x.com/elonmusk/status/1728108619189874825",
    #     "https://twitter.com/i/lists/1234567890",
    # ])
    # print("get_tweets_by_urls:", tweets)

    # 11. get_tweets_by_location
    # tweets = await scraper.get_tweets_by_location("coffee", "San Francisco", "10mi", sort="Latest", max_items=5)
    # print("get_tweets_by_location:", tweets)

    # 12. get_tweets_by_multiple_profiles
    # tweets = await scraper.get_tweets_by_multiple_profiles(["elonmusk", "naval", "paulg"], sort="Latest", max_items=5)
    # print("get_tweets_by_multiple_profiles:", tweets)

    # 13. get_tweets_by_cashtag
    # tweets = await scraper.get_tweets_by_cashtag(["BTC", "ETH", "SOL"], lang="en", max_items=5)
    # print("get_tweets_by_cashtag:", tweets)

    # 14. get_tweets_by_mention
    # tweets = await scraper.get_tweets_by_mention("NASA", sort="Latest", max_items=5)
    # print("get_tweets_by_mention:", tweets)

    # 15. get_tweets_with_media_by_handle
    # tweets = await scraper.get_tweets_with_media_by_handle("NASA", max_items=5)
    # print("get_tweets_with_media_by_handle:", tweets)

    # 16. get_tweets_with_images_by_handle
    # tweets = await scraper.get_tweets_with_images_by_handle("NASA", max_items=5)
    # print("get_tweets_with_images_by_handle:", tweets)

    # 17. get_tweets_with_videos_by_handle
    # tweets = await scraper.get_tweets_with_videos_by_handle("NASA", max_items=5)
    # print("get_tweets_with_videos_by_handle:", tweets)

    # 18. get_tweets_with_min_engagement
    # tweets = await scraper.get_tweets_with_min_engagement("bitcoin", min_likes=1000, min_retweets=100, sort="Top", max_items=5)
    # print("get_tweets_with_min_engagement:", tweets)

    # 19. get_tweets_by_verified_users
    # tweets = await scraper.get_tweets_by_verified_users("cryptocurrency", sort="Top", max_items=5)
    # print("get_tweets_by_verified_users:", tweets)

    # 20. get_tweets_excluding_retweets_by_handle
    # tweets = await scraper.get_tweets_excluding_retweets_by_handle("elonmusk", sort="Latest", max_items=5)
    # print("get_tweets_excluding_retweets_by_handle:", tweets)

    # 21. get_tweets_with_links_by_handle
    # tweets = await scraper.get_tweets_with_links_by_handle("TechCrunch", sort="Latest", max_items=5)
    # print("get_tweets_with_links_by_handle:", tweets)

    # 22. execute (raw input passthrough)
    # tweets = await scraper.execute({"searchTerms": ["from:NASA filter:media"], "sort": "Latest", "maxItems": 5})
    # print("execute:", tweets)

    # 23. search (core method with option merging)
    # tweets = await scraper.search({"searchTerms": ["from:NASA"]}, sort="Latest", max_items=5)
    # print("search:", tweets)

    # 24. search_async + RunHandle
    # run = await scraper.search_async({"searchTerms": ["from:NASA"]}, sort="Latest", max_items=5)
    # print("Run started:", run.run_id)
    # await run.wait_for_finish()
    # print("Run status:", run.status)
    # tweets = await run.get_items()
    # print("search_async items:", tweets)

    # 25. stream (async iterator)
    # count = 0
    # async for tweet in scraper.stream({"searchTerms": ["from:NASA"]}, sort="Latest", max_items=10):
    #     count += 1
    #     print(f"Tweet {count}:", tweet.get("text", "")[:80])
    # print(f"Streamed {count} tweets")

    # 26. full_response mode
    # result = await scraper.get_tweets_by_profile("NASA", sort="Latest", max_items=5, full_response=True)
    # print("Full response run_id:", result["run_id"])
    # print("Full response dataset_id:", result["dataset_id"])
    # print("Full response items count:", len(result["items"]))

    # 27. Error handling test (bad token)
    # try:
    #     bad = XScraper(token="invalid_token")
    #     await bad.get_tweets_by_profile("NASA", max_items=1)
    # except Exception as err:
    #     print("Expected error:", err)

    print("Done. Uncomment a test section in test_manual.py to run it.")


asyncio.run(main())
