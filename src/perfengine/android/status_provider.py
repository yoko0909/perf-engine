from __future__ import annotations

import re

from perfengine.app.models import PhoneStatus, utc_now_iso


class StatusProvider:
    def __init__(self, adb_client) -> None:
        self.adb_client = adb_client

    def get_phone_status(self, device_id: str, package_name: str) -> PhoneStatus:
        label = (
            self.adb_client.try_run(
                ["shell", "getprop", "ro.product.marketname"],
                serial=device_id,
            ).strip()
            or self.adb_client.try_run(
                ["shell", "getprop", "ro.product.model"],
                serial=device_id,
            ).strip()
            or device_id
        )
        battery_output = self.adb_client.try_run(
            ["shell", "dumpsys", "battery"],
            serial=device_id,
        )
        if not battery_output:
            return PhoneStatus(
                connection_state="disconnected",
                device_label=label,
                screen_state="unknown",
                app_state="unknown",
                last_updated_at=utc_now_iso(),
            )

        power_output = self.adb_client.try_run(
            ["shell", "dumpsys", "power"],
            serial=device_id,
        )
        pid_output = self.adb_client.try_run(
            ["shell", "pidof", package_name],
            serial=device_id,
        )
        battery_level = self._parse_int(battery_output, r"level:\s*(\d+)")
        raw_temperature = self._parse_int(battery_output, r"temperature:\s*(-?\d+)")
        temperature_c = raw_temperature / 10 if raw_temperature is not None else None
        return PhoneStatus(
            connection_state="connected",
            device_label=label,
            screen_state=self._parse_screen_state(power_output),
            app_state="running" if pid_output.strip() else "exited",
            battery_level=battery_level,
            temperature_c=temperature_c,
            last_updated_at=utc_now_iso(),
        )

    @staticmethod
    def _parse_int(output: str, pattern: str) -> int | None:
        match = re.search(pattern, output)
        if not match:
            return None
        return int(match.group(1))

    @staticmethod
    def _parse_screen_state(output: str) -> str:
        upper_output = output.upper()
        if "STATE=ON" in upper_output or "MWAKEFULNESS=AWAKE" in upper_output:
            return "on"
        if "STATE=OFF" in upper_output or "MWAKEFULNESS=ASLEEP" in upper_output:
            return "off"
        return "unknown"
