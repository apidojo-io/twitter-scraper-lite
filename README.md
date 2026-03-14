# x-scraper

The fastest and cheapest way to scrape tweets from X (Twitter). Battle-tested infrastructure used by tens of thousands of customers including enterprise teams.

Wraps the [Apify Twitter Scraper Lite](https://apify.com/apidojo/twitter-scraper-lite) actor with a developer-friendly, class-based API. Every method creates an Apify actor run under the hood.

## Prerequisites

- **Python 3.10+**
- An **Apify account on a paid plan** — [sign up here](https://apify.com/?fpr=yhdrb)
- An **Apify API token** — [get it here](https://console.apify.com/account/integrations)

## Installation

```bash
pip install x-scraper
```

## CLI Usage

Install the package to use from the command line:

```bash
pip install x-scraper
```

### Setup

```bash
# Store your Apify token (saved to ~/.x-scraper/config.json)
x-scraper init

# Or pass it per-command
x-scraper profile NASA --token apify_api_xxx

# Or set as environment variable
export APIFY_TOKEN=apify_api_xxx
```

### Commands

```bash
# Fetch tweets from a profile
x-scraper profile NASA --sort Latest --max-items 50

# Search by keyword
x-scraper keyword "artificial intelligence" --lang en --sort Latest

# Search by multiple keywords (joined with OR)
x-scraper keywords bitcoin ethereum solana

# Search by hashtag
x-scraper hashtag AI MachineLearning --sort Latest

# Fetch a single tweet by URL
x-scraper url https://x.com/elonmusk/status/1728108619189874825

# Fetch from multiple URLs
x-scraper urls https://x.com/a/status/1 https://x.com/b/status/2

# Tweets from a handle within a date range
x-scraper profile-date-range NASA --since 2024-01-01 --until 2024-06-01

# Tweets near a location
x-scraper location coffee --location "San Francisco" --radius 10mi

# Tweets with minimum engagement
x-scraper engagement bitcoin --min-likes 1000 --min-retweets 100

# Multiple profiles in one run
x-scraper profiles elonmusk naval paulg

# Mentions, media filters, cashtags, verified users, and more
x-scraper mention NASA
x-scraper media NASA
x-scraper images NASA
x-scraper videos NASA
x-scraper cashtag BTC ETH SOL
x-scraper verified cryptocurrency
x-scraper no-retweets elonmusk
x-scraper links TechCrunch
x-scraper conversation 1728108619189874825

# Raw actor input (full control)
x-scraper search --input '{"searchTerms":["from:NASA filter:media"]}'
x-scraper execute --input '{"searchTerms":["test"],"maxItems":10}'
```

### Output Options

```bash
# Pretty JSON (default)
x-scraper profile NASA

# Compact JSON (pipe-friendly)
x-scraper profile NASA --json

# JSONL (one object per line)
x-scraper profile NASA --jsonl

# Save to file
x-scraper profile NASA --output tweets.json

# Debug mode (shows internal logs)
x-scraper profile NASA --debug
```

### Global Flags

| Flag | Description |
|---|---|
| `--token <token>` | Apify API token (overrides env/config) |
| `--sort <order>` | `Latest`, `Top`, or `"Latest + Top"` |
| `--max-items <n>` | Maximum number of items |
| `--lang <code>` | Language filter (ISO 639-1) |
| `--timeout <secs>` | Run timeout in seconds |
| `--output <file>` | Save output to file |
| `--json` | Compact JSON output |
| `--jsonl` | JSONL output (one JSON per line) |
| `--debug` | Enable debug mode |

## Quick Start (Library)

```python
import asyncio
from x_scraper import XScraper

scraper = XScraper(token="apify_api_xxxxxxxxxxxx")

async def main():
    tweets = await scraper.get_tweets_by_profile("NASA", sort="Latest", max_items=50)
    print(tweets)

asyncio.run(main())
```

## Core Methods

### `execute(input_data, *, timeout=None, full_response=False)`

Raw passthrough — pass any valid actor input object directly. Use this when you know exactly what input the actor expects.

```python
tweets = await scraper.execute({
    "searchTerms": ["from:NASA filter:media"],
    "sort": "Latest",
    "maxItems": 100,
})
```

### `search(input_data, *, sort=None, max_items=None, lang=None, timeout=None, full_response=False)`

Run the scraper synchronously — waits for the run to finish and returns all items. Options like `sort`, `max_items`, and `lang` are merged into the input automatically.

```python
tweets = await scraper.search(
    {"searchTerms": ["from:NASA"]},
    sort="Latest", max_items=50, lang="en",
)
```

### `search_async(input_data, *, sort=None, max_items=None, lang=None)`

Start a run without waiting. Returns a `RunHandle` for polling and fetching results later. Use this for large runs that may exceed the sync timeout.

```python
run = await scraper.search_async(
    {"searchTerms": ["from:NASA"]},
    sort="Latest",
)

await run.wait_for_finish()
tweets = await run.get_items()
```

### `stream(input_data, *, sort=None, max_items=None, lang=None, timeout=None)`

Run the scraper and stream results as an async iterator. Items are yielded one by one, with auto-pagination.

```python
async for tweet in scraper.stream({"searchTerms": ["from:NASA"]}):
    print(tweet["text"])
```

## Convenience Methods

All convenience methods accept keyword arguments:

| Option | Type | Description |
|---|---|---|
| `sort` | `str` | `'Latest'`, `'Top'`, or `'Latest + Top'` |
| `max_items` | `int` | Maximum number of items to return |
| `lang` | `str` | ISO 639-1 language code (e.g. `'en'`) |
| `timeout` | `int` | Timeout in seconds (default: 120) |
| `full_response` | `bool` | Return `{"items", "run_id", "dataset_id"}` instead of just items |

### Profiles

```python
# Tweets from a single profile
tweets = await scraper.get_tweets_by_profile("NASA", sort="Latest")

# Tweets from multiple profiles in one run
tweets = await scraper.get_tweets_by_multiple_profiles(
    ["elonmusk", "naval", "paulg"],
    sort="Latest",
)

# Tweets from a handle within a date range
tweets = await scraper.get_tweets_by_handle_in_date_range(
    "NASA", "2024-01-01", "2024-06-01",
    sort="Latest",
)

# Exclude retweets from a handle
tweets = await scraper.get_tweets_excluding_retweets_by_handle("elonmusk", sort="Latest")
```

### Search

```python
# Search by keyword
tweets = await scraper.get_tweets_by_keyword("artificial intelligence", lang="en", sort="Latest")

# search_tweets is an alias for get_tweets_by_keyword
tweets = await scraper.search_tweets("artificial intelligence")

# Search by multiple keywords (joined with OR)
tweets = await scraper.get_tweets_by_keywords(
    ["bitcoin", "ethereum", "solana"],
    lang="en", sort="Latest",
)

# search_tweets_by_multiple_keywords is an alias for get_tweets_by_keywords
tweets = await scraper.search_tweets_by_multiple_keywords(["AI", "ML", "deep learning"])

# Search by hashtag
tweets = await scraper.get_tweets_by_hashtag(["AI", "MachineLearning"], sort="Latest")

# Search by cashtag
tweets = await scraper.get_tweets_by_cashtag(["BTC", "ETH", "SOL"], lang="en", sort="Latest")
```

### Single Tweet & URLs

```python
# Fetch a single tweet by URL
tweets = await scraper.get_tweet_by_url(
    "https://x.com/elonmusk/status/1728108619189874825"
)

# Fetch from multiple URLs (tweets, lists, profiles)
tweets = await scraper.get_tweets_by_urls([
    "https://x.com/elonmusk/status/1728108619189874825",
    "https://twitter.com/i/lists/1234567890",
])
```

### Conversations

```python
# Fetch replies in a conversation thread
replies = await scraper.get_tweets_by_conversation_id("1728108619189874825", sort="Latest")
```

### Mentions

```python
# Tweets mentioning a user
tweets = await scraper.get_tweets_by_mention("NASA", sort="Latest")
```

### Media Filters

```python
# Tweets with any media (images or videos)
tweets = await scraper.get_tweets_with_media_by_handle("NASA")

# Tweets with images only
tweets = await scraper.get_tweets_with_images_by_handle("NASA")

# Tweets with videos only
tweets = await scraper.get_tweets_with_videos_by_handle("NASA")

# Tweets with links
tweets = await scraper.get_tweets_with_links_by_handle("TechCrunch")
```

### Engagement & Filters

```python
# Tweets with minimum engagement
tweets = await scraper.get_tweets_with_min_engagement(
    "bitcoin", min_likes=1000, min_retweets=100, sort="Top",
)

# Tweets from verified users only
tweets = await scraper.get_tweets_by_verified_users("cryptocurrency", sort="Top")
```

### Location

```python
# Tweets near a location
tweets = await scraper.get_tweets_by_location("coffee", "San Francisco", "10mi", sort="Latest")
```

## Full Response Mode

By default, methods return just the items list. Pass `full_response=True` to get run metadata:

```python
result = await scraper.get_tweets_by_profile("NASA", sort="Latest", full_response=True)

print(result["items"])       # List of tweet dicts
print(result["run_id"])      # Apify run ID
print(result["dataset_id"]) # Apify dataset ID
```

## Async Runs with RunHandle

For large runs that may take longer than the sync timeout:

```python
run = await scraper.search_async({"searchTerms": ["from:NASA"], "sort": "Latest"})

# Poll until the run finishes
await run.wait_for_finish()

# Get all items
tweets = await run.get_items()

# Or stream items
async for tweet in run.stream():
    print(tweet["text"])

# Access run metadata
print(run.run_id)
print(run.dataset_id)
print(run.status)
```

## Error Handling

All errors from Apify are raised directly. Wrap calls in try/except:

```python
try:
    tweets = await scraper.get_tweets_by_profile("NASA")
except Exception as error:
    # Apify errors: 401 unauthorized, 404 not found, 429 rate limit, run failures
    print("Scraper error:", error)
```

The constructor raises immediately if no token is provided:

```python
try:
    scraper = XScraper()
except ValueError as error:
    # "APIFY_TOKEN is required. Pass it as: XScraper(token="apify_api_xxx")"
    pass
```

## Tweet Object Shape

Each item returned is a tweet dict:

```json
{
  "type": "tweet",
  "id": "1728108619189874825",
  "url": "https://x.com/elonmusk/status/1728108619189874825",
  "text": "More than 10 per human on average",
  "retweetCount": 11311,
  "replyCount": 6526,
  "likeCount": 104121,
  "quoteCount": 2915,
  "createdAt": "Fri Nov 24 17:49:36 +0000 2023",
  "lang": "en",
  "isReply": false,
  "isRetweet": false,
  "isQuote": true,
  "author": {
    "userName": "elonmusk",
    "name": "Elon Musk",
    "id": "44196397",
    "followers": 172669889,
    "isVerified": true,
    "isBlueVerified": true
  }
}
```

## API Reference

### Constructor

| Parameter | Type | Default | Description |
|---|---|---|---|
| `token` | `str` | *required* | Apify API token |
| `timeout` | `int` | `120` | Default timeout in seconds for sync runs |
| `debug` | `bool` | `False` | Enable debug logging |

### Core Methods

| Method | Returns | Description |
|---|---|---|
| `execute(input_data, **opts)` | `list[dict] \| dict` | Raw input passthrough |
| `search(input_data, **opts)` | `list[dict] \| dict` | Sync run with option merging |
| `search_async(input_data, **opts)` | `RunHandle` | Async run, returns handle |
| `stream(input_data, **opts)` | `AsyncIterator[dict]` | Async iterator over items |

### Convenience Methods

| Method | Parameters | Builds Query |
|---|---|---|
| `get_tweets_by_profile` | `(handle, **opts)` | `from:{handle}` |
| `get_tweets_by_handle_in_date_range` | `(handle, since, until, **opts)` | `from:{handle} since:... until:...` |
| `get_tweets_by_hashtag` | `(hashtags, **opts)` | `#tag1 #tag2` |
| `get_tweets_by_keyword` | `(keyword, **opts)` | `{keyword}` |
| `search_tweets` | `(keyword, **opts)` | Alias for `get_tweets_by_keyword` |
| `get_tweets_by_keywords` | `(keywords, **opts)` | `kw1 OR kw2 OR kw3` |
| `search_tweets_by_multiple_keywords` | `(keywords, **opts)` | Alias for `get_tweets_by_keywords` |
| `get_tweets_by_conversation_id` | `(id, **opts)` | `conversation_id:{id}` |
| `get_tweet_by_url` | `(url, **opts)` | `startUrls: [url]` |
| `get_tweets_by_urls` | `(urls, **opts)` | `startUrls: [...urls]` |
| `get_tweets_by_location` | `(query, location, radius, **opts)` | `{q} near:"{loc}" within:{r}` |
| `get_tweets_by_multiple_profiles` | `(handles, **opts)` | `["from:a","from:b"]` |
| `get_tweets_by_cashtag` | `(cashtags, **opts)` | `$X OR $Y` |
| `get_tweets_by_mention` | `(handle, **opts)` | `@{handle}` |
| `get_tweets_with_media_by_handle` | `(handle, **opts)` | `from:{handle} filter:media` |
| `get_tweets_with_images_by_handle` | `(handle, **opts)` | `from:{handle} filter:images` |
| `get_tweets_with_videos_by_handle` | `(handle, **opts)` | `from:{handle} filter:videos` |
| `get_tweets_with_min_engagement` | `(query, **opts)` | `{q} min_faves:{n} min_retweets:{n}` |
| `get_tweets_by_verified_users` | `(query, **opts)` | `{q} filter:verified` |
| `get_tweets_excluding_retweets_by_handle` | `(handle, **opts)` | `from:{handle} -filter:retweets` |
| `get_tweets_with_links_by_handle` | `(handle, **opts)` | `from:{handle} filter:links` |

### RunHandle

| Property/Method | Type | Description |
|---|---|---|
| `run_id` | `str` | The Apify run ID |
| `dataset_id` | `str` | The default dataset ID |
| `status` | `str` | Last known run status |
| `wait_for_finish(**opts)` | `RunHandle` | Poll until terminal status |
| `get_items(**opts)` | `list[dict] \| dict` | Fetch all dataset items |
| `stream()` | `AsyncIterator[dict]` | Async iterator over items |

## Pricing

This package uses the [Apify Twitter Scraper Lite](https://apify.com/apidojo/twitter-scraper-lite) actor with event-based pricing. You only pay for what you use. See the [actor pricing page](https://apify.com/apidojo/twitter-scraper-lite#pricing) for current rates.

## License

MIT
