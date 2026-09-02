import unittest

from amit_hvac_control.api.utils import (
    SettingNotConfirmedException,
    async_save_and_confirm,
    get_multipart_data,
)


class GetMultipartDataTests(unittest.TestCase):
    def test_parts_have_no_content_type_header(self):
        mp = get_multipart_data({"key1": "value1", "key2": "value2"})

        for part, _encoding, _te_encoding in mp._parts:
            self.assertNotIn("Content-Type", part.headers)

    def test_parts_have_form_data_content_disposition(self):
        mp = get_multipart_data({"key1": "value1"})

        part, _encoding, _te_encoding = mp._parts[0]
        self.assertIn('name="key1"', part.headers["Content-Disposition"])


class AsyncSaveAndConfirmTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_true_when_applied_on_first_attempt(self):
        save_calls = 0
        fetch_calls = 0

        async def save():
            nonlocal save_calls
            save_calls += 1
            return True

        async def fetch():
            nonlocal fetch_calls
            fetch_calls += 1
            return "applied"

        result = await async_save_and_confirm(
            save=save, fetch=fetch, is_applied=lambda data: data == "applied"
        )

        self.assertTrue(result)
        self.assertEqual(save_calls, 1)
        self.assertEqual(fetch_calls, 1)

    async def test_retries_until_device_reflects_the_change(self):
        # Simulates the device acking the POST with 2xx but not applying the
        # change until a later attempt - the bug that motivated this helper.
        states = iter(["stale", "stale", "applied"])
        save_calls = 0

        async def save():
            nonlocal save_calls
            save_calls += 1
            return True

        async def fetch():
            return next(states)

        result = await async_save_and_confirm(
            save=save,
            fetch=fetch,
            is_applied=lambda data: data == "applied",
            attempts=3,
            retry_delay_seconds=0,
        )

        self.assertTrue(result)
        self.assertEqual(save_calls, 3)

    async def test_retries_when_post_itself_is_not_ok(self):
        posts = iter([False, True])
        fetch_calls = 0

        async def save():
            return next(posts)

        async def fetch():
            nonlocal fetch_calls
            fetch_calls += 1
            return "applied"

        result = await async_save_and_confirm(
            save=save,
            fetch=fetch,
            is_applied=lambda data: data == "applied",
            attempts=2,
            retry_delay_seconds=0,
        )

        self.assertTrue(result)
        self.assertEqual(fetch_calls, 1)

    async def test_on_retry_fires_once_per_failed_attempt_but_not_after_the_last(self):
        states = iter(["stale", "stale", "applied"])
        retry_calls = []

        async def save():
            return True

        async def fetch():
            return next(states)

        await async_save_and_confirm(
            save=save,
            fetch=fetch,
            is_applied=lambda data: data == "applied",
            attempts=3,
            retry_delay_seconds=0,
            on_retry=lambda attempt, data: retry_calls.append((attempt, data)),
        )

        self.assertEqual(retry_calls, [(1, "stale"), (2, "stale")])

    async def test_raises_after_exhausting_attempts_without_confirmation(self):
        async def save():
            return True

        async def fetch():
            return "stale"

        with self.assertRaises(SettingNotConfirmedException):
            await async_save_and_confirm(
                save=save,
                fetch=fetch,
                is_applied=lambda data: data == "applied",
                attempts=3,
                retry_delay_seconds=0,
            )
