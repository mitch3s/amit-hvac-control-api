from __future__ import annotations

import aiohttp

from amit_hvac_control.api.temperature import TemperatureApi
from amit_hvac_control.api.ventilation import VentilationApi
from amit_hvac_control.api.status import StatusApi
from amit_hvac_control.models import Config


class AmitHvacControlClient:
    """Main client object for Amit HVAC control"""

    def __init__(self, config: Config):
        self.config = config

        self._session: aiohttp.ClientSession | None = None
        self.status_api: StatusApi | None = None
        self.temperature_api: TemperatureApi | None = None
        self.ventilation_api: VentilationApi | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            base_url=self.config.url,
            auth=aiohttp.BasicAuth(self.config.username, self.config.password),
        )
        self.status_api = StatusApi(self._session)
        self.temperature_api = TemperatureApi(self._session)
        self.ventilation_api = VentilationApi(self._session)
        return self

    async def __aexit__(self, *err):
        await self._close()

    async def _close(self):
        if self._session is None:
            return
        await self._session.close()
        self._session = None

    async def async_is_valid_auth(self):
        """Returns whether the authentication succeeded or not

        Returns:
            bool: success state of authentication
        """

        try:
            await self.async_auth_check()
            return True
        except InvalidCredentialsException:
            return False


    async def async_auth_check(self):
        """Tries to authenticate the host

        Raises:
            InvalidCredentialsException: thrown when the credentials are wrong
            HostNotReachableException: thrown when the host cannot be reached

        Returns:
            bool: returns true if successfully connected
        """
        
        try:
            res = await self._session.get("/", timeout=1)
            if res.status == 401:
                raise InvalidCredentialsException()
            return res.ok
        except (TimeoutError, aiohttp.ClientError) as err:
            raise HostNotReachableException(err)


class AuthenticationException(Exception):
    pass

class HostNotReachableException(AuthenticationException):
    pass

class InvalidCredentialsException(AuthenticationException):
    pass