import asyncio
import logging
from typing import Awaitable, Callable, Optional, TypeVar

from aiohttp import MultipartWriter

logger = logging.getLogger(__name__)


def get_multipart_data(post: dict):
    with MultipartWriter("form-data") as mp:
        for key, value in post.items():
            part = mp.append(str(value))

            del part.headers["Content-Type"]
            part.set_content_disposition("form-data", name=key)
        return mp


class SettingNotConfirmedException(Exception):
    """Raised when the controller never reflects a setting that was posted to it."""


T = TypeVar("T")


async def async_save_and_confirm(
    save: Callable[[], Awaitable[bool]],
    fetch: Callable[[], Awaitable[T]],
    is_applied: Callable[[T], bool],
    *,
    attempts: int = 3,
    retry_delay_seconds: float = 1.0,
    on_retry: Optional[Callable[[int, Optional[T]], None]] = None,
) -> bool:
    """POST a setting and confirm the controller actually applied it.

    The controller sometimes acknowledges a POST with a 2xx response while
    silently dropping the change, so a successful HTTP response alone doesn't
    mean the setting took effect. This re-fetches the current state after
    each attempt and retries until it matches, raising if it never does.

    `on_retry`, if given, is called after an attempt fails to apply (before
    the retry delay) with the 1-based attempt number and the fetched state
    (or `None` if the POST itself wasn't acknowledged).
    """
    for attempt in range(1, attempts + 1):
        data = None
        if await save():
            data = await fetch()
            if is_applied(data):
                return True
        if attempt < attempts:
            logger.debug(
                "Setting not applied yet after attempt %d/%d, retrying: %r",
                attempt,
                attempts,
                data,
            )
            if on_retry is not None:
                on_retry(attempt, data)
            await asyncio.sleep(retry_delay_seconds)

    raise SettingNotConfirmedException(
        f"Device did not confirm the setting after {attempts} attempts"
    )
