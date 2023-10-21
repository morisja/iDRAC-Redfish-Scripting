import logging
import json
import requests
from typing import List

log = logging.getLogger()


class IdracManagerException(Exception):
    pass


class AuthException(IdracManagerException):
    pass


class GenericError(IdracManagerException):
    pass


class IdracManager:
    def __init__(self, args: dict):
        self.ip = args["ip"]
        self.username = args["u"]
        self.password = args["p"]
        self.ssl = args["ssl"].lower() == "true"
        self.verify_cert = args["ssl"].lower() == "true"
        self.x_auth_token = args["x"]

    def headers(self, additional: dict = {}):
        headers = {}
        headers.update(additional)
        if self.x_auth_token:
            headers.update({"X-Auth-Token": self.x_auth_token})
        return headers

    @property
    def auth(self):
        if not self.x_auth_token:
            return (self.username, self.password)
        return ()

    def _make_url(self, url: str) -> str:
        return f"https://{self.ip}/{url}"

    def _doget(self, url: str, override_codes: List[int] = None) -> requests.Response:
        valid_codes = [201]
        response = requests.get(
            self._make_url(url),
            verify=self.verify_cert,
            headers=self.headers(),
            auth=self.auth,
        )
        if override_codes:
            valid_codes = override_codes
        if response.status_code == 401:
            raise AuthException()
        if response.status_code not in valid_codes:
            raise GenericError()
        return response

    def _dopost(
        self, url: str, payload: dict = {}, override_codes=None
    ) -> requests.Response:
        valid_codes = [201, 204]
        if override_codes:
            valid_codes = override_codes
        response = requests.post(
            self._make_url(url),
            data=json.dumps(payload),
            headers=self.headers({"additional": "foo"}),
            auth=self.auth,
        )
        if response.status_code == 401:
            raise AuthException()
        if response.status_code not in valid_codes:
            raise GenericError()
        return response

    def get_storage_controllers(self) -> requests.Response:
        return self._doget(f"redfish/v1/Systems/System.Embedded.1/Storage")

    def get_storage_controller_detail(self, controller_fqdd: str) -> requests.Response:
        return self._doget(
            f"redfish/v1/Systems/System.Embedded.1/Storage/{controller_fqdd}"
        )

    def get_storage_drive(self, id: str) -> requests.Response:
        return self._doget("/redfish/v1/Systems/System.Embedded.1/Storage/Drives/{id}")

    def get_drive(self, drive: str) -> requests.Response:
        return self._doget(
            f"redfish/v1/Systems/System.Embedded.1/Storage/Drives/{drive}"
        ).json()

    def get_chassis(self) -> requests.Response:
        return self._doget(f"redfish/v1/Chassis")

    def check_supported_idrac_version(self) -> None:
        self._doget("/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService")

    def do_powercontrol(self, action: str) -> requests.Response:
        return self._dopost(
            f"redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset",
            {"ResetType": action},
        )

    def do_blink(self) -> None:
        payload = {"TargetFQDD": True}
        self._dopost(
            "redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.BlinkTarget",
            payload=payload,
        )

    def do_unblink(self) -> None:
        payload = {"TargetFQDD": True}
        self._dopost(
            "redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.UnBlinkTarget",
            payload=payload,
        )
