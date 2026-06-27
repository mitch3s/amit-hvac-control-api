import unittest

import aiohttp

from amit_hvac_control.client import (
    AmitHvacControlClient,
    HostNotReachableException,
    InvalidCredentialsException,
)


class FakeResponse:
    def __init__(self, status):
        self.status = status
        self.ok = status < 400


class FakeSession:
    def __init__(self, exc=None, response=None):
        self._exc = exc
        self._response = response
        self.closed = False

    async def get(self, *args, **kwargs):
        if self._exc is not None:
            raise self._exc
        return self._response

    async def close(self):
        self.closed = True


def _make_client(session):
    client = object.__new__(AmitHvacControlClient)
    client._session = session
    return client


class ClientAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_connection_refused_raises_host_not_reachable(self):
        client = _make_client(
            FakeSession(exc=aiohttp.ClientConnectorError(connection_key=None, os_error=OSError()))
        )

        with self.assertRaises(HostNotReachableException):
            await client.async_auth_check()

    async def test_timeout_raises_host_not_reachable(self):
        client = _make_client(FakeSession(exc=TimeoutError()))

        with self.assertRaises(HostNotReachableException):
            await client.async_auth_check()

    async def test_unauthorized_raises_invalid_credentials(self):
        client = _make_client(FakeSession(response=FakeResponse(401)))

        with self.assertRaises(InvalidCredentialsException):
            await client.async_auth_check()

    async def test_is_valid_auth_false_on_invalid_credentials(self):
        client = _make_client(FakeSession(response=FakeResponse(401)))

        self.assertFalse(await client.async_is_valid_auth())

    async def test_is_valid_auth_propagates_host_not_reachable(self):
        client = _make_client(FakeSession(exc=TimeoutError()))

        with self.assertRaises(HostNotReachableException):
            await client.async_is_valid_auth()

    async def test_close_is_idempotent(self):
        session = FakeSession(response=FakeResponse(200))
        client = _make_client(session)

        await client._close()
        await client._close()

        self.assertTrue(session.closed)
        self.assertIsNone(client._session)


if __name__ == "__main__":
    unittest.main()
