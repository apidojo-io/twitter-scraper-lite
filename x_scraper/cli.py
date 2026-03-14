#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import click
from apify_client import ApifyClientAsync

from .scraper import XScraper

CONFIG_DIR = Path.home() / ".x-scraper"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")


def resolve_token(token: str | None) -> str:
    resolved = token or os.environ.get("APIFY_TOKEN") or load_config().get("token")

    if not resolved:
        click.echo(
            "Error: No Apify token found.\n\n"
            "Provide one via:\n"
            "  1. --token <token> flag\n"
            "  2. APIFY_TOKEN environment variable\n"
            '  3. Run "x-scraper init" to store your token\n',
            err=True,
        )
        sys.exit(1)

    return resolved


def format_output(items: list[dict], *, use_json: bool = False, use_jsonl: bool = False) -> str:
    if use_jsonl:
        return "\n".join(json.dumps(item) for item in items)
    if use_json:
        return json.dumps(items)
    return json.dumps(items, indent=2)


def write_output(formatted: str, output_file: str | None) -> None:
    if output_file:
        Path(output_file).write_text(formatted + "\n")
        click.echo(f"Wrote {output_file}", err=True)
    else:
        click.echo(formatted)


def build_search_options(ctx_params: dict) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if ctx_params.get("sort") is not None:
        options["sort"] = ctx_params["sort"]
    if ctx_params.get("max_items") is not None:
        options["max_items"] = ctx_params["max_items"]
    if ctx_params.get("lang") is not None:
        options["lang"] = ctx_params["lang"]
    if ctx_params.get("timeout") is not None:
        options["timeout"] = ctx_params["timeout"]
    return options


def run_command(ctx_params: dict, coro_fn) -> None:
    """Resolve token, run the async scraper function, format and output results."""
    try:
        token = resolve_token(ctx_params.get("token"))
        search_opts = build_search_options(ctx_params)

        async def _run():
            scraper = XScraper(token=token, debug=bool(ctx_params.get("debug")))
            return await coro_fn(scraper, search_opts)

        items = asyncio.run(_run())
        formatted = format_output(
            items,
            use_json=bool(ctx_params.get("json")),
            use_jsonl=bool(ctx_params.get("jsonl")),
        )
        write_output(formatted, ctx_params.get("output"))
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


GLOBAL_OPTIONS = [
    click.option("--token", default=None, help="Apify API token"),
    click.option("--sort", default=None, help='Sort order: Latest, Top, or "Latest + Top"'),
    click.option("--max-items", type=int, default=None, help="Maximum number of items"),
    click.option("--lang", default=None, help="Language filter (ISO 639-1)"),
    click.option("--timeout", type=int, default=None, help="Run timeout in seconds"),
    click.option("--output", default=None, help="Save output to file instead of stdout"),
    click.option("--json", "json", is_flag=True, default=False, help="Compact JSON output"),
    click.option("--jsonl", is_flag=True, default=False, help="JSONL output (one JSON object per line)"),
    click.option("--debug", is_flag=True, default=False, help="Enable debug mode"),
]


def add_global_options(func):
    for option in reversed(GLOBAL_OPTIONS):
        func = option(func)
    return func


@click.group()
@click.version_option("1.0.0", prog_name="x-scraper")
def cli():
    """The fastest and cheapest way to scrape tweets from X (Twitter)."""


@cli.command()
def init():
    """Interactively set up your Apify API token."""
    click.echo("x-scraper init — configure your Apify API token\n", err=True)

    token = click.prompt("Enter your Apify API token", default="", show_default=False)

    if not token:
        click.echo("No token provided. Aborting.", err=True)
        sys.exit(1)

    click.echo("Validating token...", err=True)

    async def _validate():
        client = ApifyClientAsync(token=token)
        return await client.user().get()

    try:
        user = asyncio.run(_validate())
        identity = user.get("username") or user.get("email") or "unknown"
        click.echo(f"Authenticated as: {identity}", err=True)
    except Exception:
        click.echo("Error: Invalid token — could not authenticate with Apify.", err=True)
        sys.exit(1)

    config = load_config()
    config["token"] = token
    save_config(config)

    click.echo(f"\nToken saved to {CONFIG_FILE}", err=True)
    click.echo("You can now use x-scraper commands without --token.", err=True)


@cli.command()
@click.option("--input", "input_json", required=True, help="Actor input as JSON string")
@add_global_options
def search(input_json, **opts):
    """Run the scraper with raw actor input (JSON)."""
    run_command(opts, lambda scraper, o: scraper.search(json.loads(input_json), **o))


@cli.command()
@click.option("--input", "input_json", required=True, help="Actor input as JSON string")
@add_global_options
def execute(input_json, **opts):
    """Execute the scraper with raw actor input (no option merging)."""
    run_command(opts, lambda scraper, o: scraper.execute(json.loads(input_json), **o))


@cli.command()
@click.argument("handle")
@add_global_options
def profile(handle, **opts):
    """Fetch tweets from a Twitter/X profile."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_by_profile(handle, **o))


@cli.command("profile-date-range")
@click.argument("handle")
@click.option("--since", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--until", "until_date", required=True, help="End date (YYYY-MM-DD)")
@add_global_options
def profile_date_range(handle, since, until_date, **opts):
    """Fetch tweets from a handle within a date range."""
    run_command(
        opts,
        lambda scraper, o: scraper.get_tweets_by_handle_in_date_range(handle, since, until_date, **o),
    )


@cli.command()
@click.argument("tags", nargs=-1, required=True)
@add_global_options
def hashtag(tags, **opts):
    """Fetch tweets by hashtag(s)."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_by_hashtag(list(tags), **o))


@cli.command()
@click.argument("keyword")
@add_global_options
def keyword(keyword, **opts):
    """Search tweets by a single keyword or phrase."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_by_keyword(keyword, **o))


@cli.command()
@click.argument("keywords", nargs=-1, required=True)
@add_global_options
def keywords(keywords, **opts):
    """Search tweets by multiple keywords (joined with OR)."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_by_keywords(list(keywords), **o))


@cli.command()
@click.argument("id")
@add_global_options
def conversation(id, **opts):
    """Fetch replies in a conversation thread."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_by_conversation_id(id, **o))


@cli.command()
@click.argument("url")
@add_global_options
def url(url, **opts):
    """Fetch a single tweet by URL."""
    run_command(opts, lambda scraper, o: scraper.get_tweet_by_url(url, **o))


@cli.command()
@click.argument("urls", nargs=-1, required=True)
@add_global_options
def urls(urls, **opts):
    """Fetch tweets from multiple URLs."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_by_urls(list(urls), **o))


@cli.command()
@click.argument("query")
@click.option("--location", required=True, help='Location name (e.g. "San Francisco")')
@click.option("--radius", required=True, help='Search radius (e.g. "10mi", "25km")')
@add_global_options
def location(query, location, radius, **opts):
    """Search tweets near a geographic location."""
    run_command(
        opts,
        lambda scraper, o: scraper.get_tweets_by_location(query, location, radius, **o),
    )


@cli.command()
@click.argument("handles", nargs=-1, required=True)
@add_global_options
def profiles(handles, **opts):
    """Fetch tweets from multiple profiles in one run."""
    run_command(
        opts,
        lambda scraper, o: scraper.get_tweets_by_multiple_profiles(list(handles), **o),
    )


@cli.command()
@click.argument("tags", nargs=-1, required=True)
@add_global_options
def cashtag(tags, **opts):
    """Fetch tweets by cashtag(s) (e.g. $BTC)."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_by_cashtag(list(tags), **o))


@cli.command()
@click.argument("handle")
@add_global_options
def mention(handle, **opts):
    """Fetch tweets mentioning a user."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_by_mention(handle, **o))


@cli.command()
@click.argument("handle")
@add_global_options
def media(handle, **opts):
    """Fetch tweets with media (images or videos) from a handle."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_with_media_by_handle(handle, **o))


@cli.command()
@click.argument("handle")
@add_global_options
def images(handle, **opts):
    """Fetch tweets with images from a handle."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_with_images_by_handle(handle, **o))


@cli.command()
@click.argument("handle")
@add_global_options
def videos(handle, **opts):
    """Fetch tweets with videos from a handle."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_with_videos_by_handle(handle, **o))


@cli.command()
@click.argument("query")
@click.option("--min-likes", type=int, default=None, help="Minimum likes")
@click.option("--min-retweets", type=int, default=None, help="Minimum retweets")
@click.option("--min-replies", type=int, default=None, help="Minimum replies")
@add_global_options
def engagement(query, min_likes, min_retweets, min_replies, **opts):
    """Fetch tweets with minimum engagement thresholds."""
    engagement_opts: dict[str, Any] = {}
    if min_likes is not None:
        engagement_opts["min_likes"] = min_likes
    if min_retweets is not None:
        engagement_opts["min_retweets"] = min_retweets
    if min_replies is not None:
        engagement_opts["min_replies"] = min_replies

    run_command(
        opts,
        lambda scraper, o: scraper.get_tweets_with_min_engagement(query, **engagement_opts, **o),
    )


@cli.command()
@click.argument("query")
@add_global_options
def verified(query, **opts):
    """Fetch tweets from verified users matching a query."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_by_verified_users(query, **o))


@cli.command("no-retweets")
@click.argument("handle")
@add_global_options
def no_retweets(handle, **opts):
    """Fetch tweets from a handle, excluding retweets."""
    run_command(
        opts,
        lambda scraper, o: scraper.get_tweets_excluding_retweets_by_handle(handle, **o),
    )


@cli.command()
@click.argument("handle")
@add_global_options
def links(handle, **opts):
    """Fetch tweets with links from a handle."""
    run_command(opts, lambda scraper, o: scraper.get_tweets_with_links_by_handle(handle, **o))


def main():
    cli()


if __name__ == "__main__":
    main()
