from __future__ import annotations

import time
from typing import Any, AsyncIterator

from apify_client import ApifyClientAsync

from .constants import DATASET_PAGE_LIMIT, TERMINAL_STATUSES


class RunHandle:
    """Handle for an asynchronous actor run returned by :meth:`XScraper.search_async`.

    Provides methods to poll for completion, fetch results, and stream items.
    """

    def __init__(self, run_data: dict[str, Any], client: ApifyClientAsync) -> None:
        self._run_data = run_data
        self._client = client

    @property
    def run_id(self) -> str:
        """The Apify run ID."""
        return self._run_data["id"]

    @property
    def dataset_id(self) -> str:
        """The default dataset ID for this run."""
        return self._run_data["defaultDatasetId"]

    @property
    def status(self) -> str:
        """Last known status (READY, RUNNING, SUCCEEDED, FAILED, ABORTING, ABORTED, TIMED-OUT)."""
        return self._run_data["status"]

    async def wait_for_finish(self, *, wait_secs: int = 999_999) -> RunHandle:
        """Poll until the run reaches a terminal status.

        Uses the Apify API's long-polling mechanism: each request blocks
        server-side for up to 60 seconds.

        Args:
            wait_secs: Maximum total time to wait in seconds.

        Returns:
            This instance with updated status.

        Raises:
            RuntimeError: If the run finishes with a non-SUCCEEDED status.
            TimeoutError: If the wait budget expires while the run is still going.
        """
        deadline = time.monotonic() + wait_secs
        poll_interval_secs = 60

        while True:
            remaining_secs = max(0, int(deadline - time.monotonic()) + 1)
            poll_secs = min(poll_interval_secs, remaining_secs)

            updated = await self._client.run(self.run_id).wait_for_finish(wait_secs=poll_secs)
            self._run_data = updated

            if updated["status"] in TERMINAL_STATUSES:
                if updated["status"] != "SUCCEEDED":
                    raise RuntimeError(
                        f"Run {self.run_id} finished with status: {updated['status']}"
                    )
                return self

            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Run {self.run_id} did not finish within {wait_secs}s "
                    f"(current status: {updated['status']})"
                )

    async def get_items(self, *, full_response: bool = False) -> list[dict] | dict:
        """Fetch all items from the run's dataset with auto-pagination.

        Args:
            full_response: If True, returns ``{"items", "run_id", "dataset_id"}``
                instead of just the items list.

        Returns:
            List of tweet dicts, or a full-response dict.

        Raises:
            RuntimeError: If the run has not succeeded.
        """
        if self._run_data["status"] not in TERMINAL_STATUSES:
            await self.wait_for_finish()

        if self._run_data["status"] != "SUCCEEDED":
            raise RuntimeError(
                f"Run {self.run_id} finished with status: {self._run_data['status']}"
            )

        all_items: list[dict] = []
        offset = 0

        while True:
            result = await self._client.dataset(self.dataset_id).list_items(
                offset=offset, limit=DATASET_PAGE_LIMIT, clean=True
            )
            items = result.items

            all_items.extend(items)

            if len(items) < DATASET_PAGE_LIMIT:
                break
            offset += len(items)

        if full_response:
            return {"items": all_items, "run_id": self.run_id, "dataset_id": self.dataset_id}

        return all_items

    async def stream(self) -> AsyncIterator[dict]:
        """Async iterator that yields tweet items one by one from the run's dataset.

        Auto-paginates through pages internally. The run must finish before iterating.

        Yields:
            A single tweet item dict.
        """
        if self._run_data["status"] not in TERMINAL_STATUSES:
            await self.wait_for_finish()

        if self._run_data["status"] != "SUCCEEDED":
            raise RuntimeError(
                f"Run {self.run_id} finished with status: {self._run_data['status']}"
            )

        offset = 0

        while True:
            result = await self._client.dataset(self.dataset_id).list_items(
                offset=offset, limit=DATASET_PAGE_LIMIT, clean=True
            )
            items = result.items

            for item in items:
                yield item

            if len(items) < DATASET_PAGE_LIMIT:
                break
            offset += len(items)
