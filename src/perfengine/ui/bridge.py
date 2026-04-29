from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum


def to_json_ready(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: to_json_ready(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: to_json_ready(item) for key, item in value.items()}
    return value


class BridgeApi:
    def __init__(self, service) -> None:
        self.service = service

    def list_devices(self):
        return to_json_ready(self.service.list_devices())

    def list_apps(self, device_id: str):
        return to_json_ready(self.service.list_apps(device_id))

    def start_session(self, device_id: str, package_name: str):
        return to_json_ready(self.service.start_session(device_id, package_name))

    def stop_session(self):
        return to_json_ready(self.service.stop_session())

    def get_live_snapshot(self):
        return to_json_ready(self.service.get_live_snapshot())
