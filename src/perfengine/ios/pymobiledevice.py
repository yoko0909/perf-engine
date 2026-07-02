from __future__ import annotations

import asyncio
import importlib
import io
import inspect
import json
import logging
import plistlib
import struct
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, fields
from typing import Any
from urllib.request import urlopen as default_urlopen

from perfengine.app.errors import OperatorError


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IOSProcessStatus:
    pid: int | None
    running: bool
    name: str | None = None


@dataclass(slots=True)
class IOSSystemSnapshot:
    app_cpu_percent: float | None = None
    total_cpu_percent: float | None = None
    phys_footprint: int | None = None
    memory_mb: float | None = None


@dataclass(slots=True)
class IOSBatterySnapshot:
    battery_level: int | None = None
    temperature_c: float | None = None


@dataclass(slots=True)
class IOSCollectorSnapshot:
    fps: dict[str, Any] | None = None
    system: IOSSystemSnapshot | None = None
    battery: IOSBatterySnapshot | None = None


class PymobiledeviceIOSAdapter:
    def __init__(
        self,
        *,
        create_using_usbmux: Callable[..., Awaitable[Any]] | None = None,
        list_usbmux_devices: Callable[[], Awaitable[Any] | Any] | None = None,
        installation_proxy_factory: Callable[[Any], Any] | None = None,
        remote_service_discovery_factory: Callable[[tuple[str, int]], Any] | None = None,
        dvt_service_factory: Callable[[Any], Any] | None = None,
        process_control_factory: Callable[[Any], Any] | None = None,
        sysmontap_factory: Callable[[Any], Any] | None = None,
        graphics_factory: Callable[[Any], Any] | None = None,
        tunnel_urlopen=None,
        remote_connect_attempts: int = 3,
        remote_connect_retry_interval_s: float = 2.0,
    ) -> None:
        self.create_using_usbmux = create_using_usbmux or self._default_create_using_usbmux
        self.list_usbmux_devices = list_usbmux_devices or self._default_list_usbmux_devices
        self.installation_proxy_factory = installation_proxy_factory or self._default_installation_proxy
        self.remote_service_discovery_factory = (
            remote_service_discovery_factory or self._default_remote_service_discovery
        )
        self.dvt_service_factory = dvt_service_factory or self._default_dvt_service
        self.process_control_factory = process_control_factory or self._default_process_control
        self.sysmontap_factory = sysmontap_factory or self._default_sysmontap
        self.graphics_factory = graphics_factory or self._default_graphics
        self.tunnel_urlopen = tunnel_urlopen or default_urlopen
        self.remote_connect_attempts = max(1, remote_connect_attempts)
        self.remote_connect_retry_interval_s = max(0.0, remote_connect_retry_interval_s)
        self._runner: asyncio.Runner | None = None
        self.lockdown = None
        self.developer_provider = None
        self.device_id: str | None = None
        self.dvt = None
        self.process_control = None
        self.sysmontap = None
        self._sysmontap_iter = None
        self.graphics = None
        self._graphics_iter = None
        self.diagnostics = None
        self._owned_services: list[Any] = []
        self._active_pid: int | None = None
        self._latest_system_snapshot = IOSSystemSnapshot()
        self._latest_fps_sample: dict[str, Any] = {}
        self._previous_process_cpu: tuple[float, float] | None = None

    @staticmethod
    async def _default_create_using_usbmux(*, serial: str):
        try:
            from pymobiledevice3.lockdown import create_using_usbmux
        except Exception as exc:
            raise PymobiledeviceIOSAdapter._unavailable_import_error(exc, phase="import lockdown") from exc
        return await _maybe_await(create_using_usbmux(serial=serial))

    @staticmethod
    async def _default_list_usbmux_devices():
        try:
            from pymobiledevice3.lockdown import usbmux
        except Exception as exc:
            raise PymobiledeviceIOSAdapter._unavailable_import_error(exc, phase="import usbmux") from exc
        return await _maybe_await(usbmux.list_devices())

    @staticmethod
    def _default_installation_proxy(lockdown):
        try:
            from pymobiledevice3.services.installation_proxy import InstallationProxyService
        except Exception as exc:
            raise PymobiledeviceIOSAdapter._unavailable_import_error(exc, phase="import installation proxy") from exc
        return InstallationProxyService(lockdown)

    @staticmethod
    def _default_remote_service_discovery(address: tuple[str, int]):
        try:
            from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
        except Exception as exc:
            raise PymobiledeviceIOSAdapter._unavailable_import_error(
                exc, phase="import remote service discovery"
            ) from exc
        return RemoteServiceDiscoveryService(address)

    @staticmethod
    def _default_dvt_service(service_provider):
        try:
            module = importlib.import_module("pymobiledevice3.services.dvt.dvt_secure_socket_proxy")
            dvt_service_cls = getattr(module, "DvtSecureSocketProxyService")
            return dvt_service_cls(lockdown=service_provider)
        except Exception as primary_exc:
            logger.info(
                "Demo-style DVT secure socket proxy unavailable; falling back to DvtProvider: %s: %s",
                type(primary_exc).__name__,
                primary_exc,
            )
        try:
            module = importlib.import_module("pymobiledevice3.services.dvt.instruments.dvt_provider")
            dvt_provider_cls = getattr(module, "DvtProvider")
        except Exception as exc:
            raise PymobiledeviceIOSAdapter._unavailable_import_error(
                exc, phase="import dvt provider"
            ) from exc
        return dvt_provider_cls(service_provider)

    @staticmethod
    def _default_process_control(dvt):
        try:
            from pymobiledevice3.services.dvt.instruments.process_control import ProcessControl
        except Exception as exc:
            raise PymobiledeviceIOSAdapter._unavailable_import_error(exc, phase="import process control") from exc
        return ProcessControl(dvt)

    @staticmethod
    def _default_sysmontap(dvt):
        try:
            module = importlib.import_module("pymobiledevice3.services.dvt.instruments.sysmontap")
            sysmontap_cls = getattr(module, "Sysmontap")
        except Exception as exc:
            raise PymobiledeviceIOSAdapter._unavailable_import_error(exc, phase="import sysmontap") from exc
        create = getattr(sysmontap_cls, "create", None)
        if create is not None:
            return create(dvt)
        return sysmontap_cls(dvt)

    @staticmethod
    def _default_graphics(dvt):
        try:
            module = importlib.import_module("pymobiledevice3.services.dvt.instruments.graphics")
            graphics_cls = getattr(module, "Graphics")
        except Exception as exc:
            raise PymobiledeviceIOSAdapter._unavailable_import_error(exc, phase="import graphics") from exc
        return graphics_cls(dvt)

    @staticmethod
    def _unavailable_import_error(exc: Exception, *, phase: str) -> OperatorError:
        logger.exception(
            "iOS pymobiledevice dependency unavailable during %s: %s: %s",
            phase,
            type(exc).__name__,
            exc,
        )
        return OperatorError(
            code="ios_pymobiledevice_unavailable",
            message="iOS device support is not available. Reinstall the tool package.",
        )

    def _run_async(self, awaitable: Awaitable[Any]) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                if self._runner is None:
                    self._runner = asyncio.Runner()
                return self._runner.run(awaitable)
            except OperatorError:
                raise
            except Exception as exc:
                raise _map_pymobiledevice_error(exc, phase="async operation") from exc
        raise OperatorError(
            code="ios_async_context_unsupported",
            message="iOS device communication cannot run inside an existing event loop.",
        )

    def _resolve(self, value: Any) -> Any:
        if inspect.isawaitable(value):
            return self._run_async(value)
        return value

    def connect(self, device_id: str, *, tunnel_info_url: str | None = None) -> None:
        self.lockdown = self._run_async(_maybe_await(self.create_using_usbmux(serial=device_id)))
        self.device_id = device_id
        if tunnel_info_url:
            self.developer_provider = self._run_async(
                self._connect_remote_developer_provider(device_id, tunnel_info_url)
            )

    async def _connect_remote_developer_provider(self, device_id: str, tunnel_info_url: str):
        address = self._remote_service_address(device_id, tunnel_info_url)
        logger.info("Connecting iOS remote developer services for %s at %s:%s", device_id, address[0], address[1])
        provider = self.remote_service_discovery_factory(address)
        connect = getattr(provider, "connect", None)
        if connect is not None:
            last_exc: Exception | None = None
            for attempt in range(1, self.remote_connect_attempts + 1):
                try:
                    await _maybe_await(connect())
                    break
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "iOS remote developer service connect failed for %s at %s:%s, attempt %s/%s: %s: %s",
                        device_id,
                        address[0],
                        address[1],
                        attempt,
                        self.remote_connect_attempts,
                        type(exc).__name__,
                        exc,
                    )
                    if attempt < self.remote_connect_attempts:
                        await asyncio.sleep(self.remote_connect_retry_interval_s)
            else:
                assert last_exc is not None
                raise _map_pymobiledevice_error(last_exc, phase="connect remote developer provider") from last_exc
        self._owned_services.append(provider)
        return provider

    def _remote_service_address(self, device_id: str, tunnel_info_url: str) -> tuple[str, int]:
        response = self.tunnel_urlopen(tunnel_info_url, timeout=1.0)
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
        address = _extract_tunnel_address(payload, device_id)
        if address is None:
            raise OperatorError(
                code="ios_tunnel_unavailable",
                message="iOS tunnel is not ready for this iPhone. Reconnect it and try again.",
            )
        return address

    async def _list_devices(self) -> list[dict[str, Any]]:
        devices = await _maybe_await(self.list_usbmux_devices())
        normalized = []
        for device in devices or []:
            serial = _object_value(device, "serial", "udid", "identifier", "Identifier", default="")
            if not serial:
                continue
            connection_type = _connection_type(device)
            info: dict[str, Any] = {
                "udid": serial,
                "ConnectionType": connection_type,
            }
            try:
                lockdown = await _maybe_await(self.create_using_usbmux(serial=serial))
            except OperatorError:
                raise
            except Exception:
                lockdown = None
            short_info = _object_value(lockdown, "short_info", default={}) if lockdown is not None else {}
            if isinstance(short_info, dict):
                info.update(short_info)
            info.setdefault("DeviceName", _object_value(device, "device_name", "name", default=serial))
            info.setdefault("ProductType", _object_value(lockdown, "product_type", default=""))
            info.setdefault("ProductVersion", _object_value(lockdown, "product_version", default=""))
            normalized.append(info)
        return normalized

    def list_devices(self) -> list[dict[str, Any]]:
        return self._run_async(self._list_devices())

    async def _read_apps(self, device_id: str) -> list[dict[str, Any]]:
        if self.lockdown is None or self.device_id != device_id:
            self.lockdown = await _maybe_await(self.create_using_usbmux(serial=device_id))
            self.device_id = device_id
        service = self.installation_proxy_factory(self.lockdown)
        try:
            connect = getattr(service, "connect", None)
            if connect is not None:
                await _maybe_await(connect())
            apps = await _get_user_apps(service)
            return _normalize_app_payload(apps)
        finally:
            close = getattr(service, "close", None)
            if close is not None:
                await _maybe_await(close())

    def list_apps(self, device_id: str) -> list[dict[str, Any]]:
        return self._run_async(self._read_apps(device_id))

    async def _create_process_control(self):
        service_provider = self.developer_provider or self.lockdown
        if service_provider is None:
            raise OperatorError(
                code="ios_device_not_ready",
                message="iPhone communication is not ready. Start the session again.",
            )
        try:
            dvt_service = self.dvt_service_factory(service_provider)
            dvt = await _enter_service(dvt_service)
            process_control = self.process_control_factory(dvt)
            connect = getattr(process_control, "connect", None)
            if connect is not None:
                await _maybe_await(connect())
        except OperatorError as exc:
            logger.exception("iOS create process control failed with operator error %s", exc.code)
            raise
        except Exception as exc:
            raise _map_pymobiledevice_error(exc, phase="create process control") from exc
        self.dvt = dvt
        self.process_control = process_control
        self._owned_services.extend([dvt_service, process_control])
        return process_control

    def get_process_status(self, package_name: str) -> IOSProcessStatus:
        process_control = self.process_control or self._run_async(self._create_process_control())
        try:
            pid = self._resolve(process_control.process_identifier_for_bundle_identifier(package_name))
        except OperatorError as exc:
            logger.exception("iOS sysmontap start failed with operator error %s", exc.code)
            raise
        except Exception as exc:
            raise _map_pymobiledevice_error(exc, phase="query process status") from exc
        if not pid:
            return IOSProcessStatus(pid=None, running=False)
        return IOSProcessStatus(pid=pid, running=True)

    def prepare_developer_services(self) -> None:
        if self.process_control is None:
            self._run_async(self._create_process_control())

    async def _start_sysmontap(self):
        if self.dvt is None:
            await self._create_process_control()
        try:
            sysmontap_service = await _maybe_await(self.sysmontap_factory(self.dvt))
            sysmontap = await _enter_service(sysmontap_service)
        except OperatorError:
            raise
        except Exception as exc:
            raise _map_pymobiledevice_error(exc, phase="start sysmontap") from exc
        self.sysmontap = sysmontap
        self._sysmontap_iter = _iter_service(sysmontap)
        self._owned_services.append(sysmontap_service)

    async def _start_graphics(self):
        if self.dvt is None:
            await self._create_process_control()
        try:
            graphics_service = await _maybe_await(self.graphics_factory(self.dvt))
            graphics = await _enter_service(graphics_service)
        except OperatorError:
            raise
        except Exception as exc:
            raise _map_pymobiledevice_error(exc, phase="start graphics") from exc
        self.graphics = graphics
        self._graphics_iter = _iter_service(graphics)
        self._owned_services.append(graphics_service)

    def start_collectors(self, pid: int) -> None:
        self._active_pid = pid
        self._previous_process_cpu = None
        if self.sysmontap is None:
            try:
                self._run_async(self._start_sysmontap())
            except Exception:
                self.stop_collectors()
                self.close()
                raise

    def stop_collectors(self) -> None:
        self._active_pid = None
        self._previous_process_cpu = None

    def read_system_sample(self) -> IOSSystemSnapshot:
        if self._sysmontap_iter is not None and self.sysmontap is not None:
            try:
                row = _next_service_item(self._sysmontap_iter, self._run_async)
            except (StopIteration, StopAsyncIteration):
                return self._latest_system_snapshot
            process_fields = [field.name for field in fields(self.sysmontap.process_attributes_cls)]
            self._record_sysmontap_sample(row, process_fields=process_fields, timestamp=time.monotonic())
        return self._latest_system_snapshot

    async def _read_battery_payload(self) -> dict[str, Any]:
        if self.lockdown is None:
            raise OperatorError(
                code="ios_device_not_ready",
                message="iPhone communication is not ready. Start the session again.",
            )
        if self.diagnostics is None:
            try:
                from pymobiledevice3.services.diagnostics import DiagnosticsService
            except Exception as exc:
                raise OperatorError(
                    code="ios_pymobiledevice_unavailable",
                    message="iOS device support is not available. Reinstall the tool package.",
                ) from exc
            diagnostics = DiagnosticsService(self.lockdown)
            await diagnostics.connect()
            self.diagnostics = diagnostics
            self._owned_services.append(diagnostics)
        return await self.diagnostics.get_battery()

    def read_battery_sample(self) -> IOSBatterySnapshot:
        return self._map_battery_snapshot(self._run_async(self._read_battery_payload()))

    async def _read_coreprofile_metadata(self, *, timeout: float = 1.0) -> dict[str, Any]:
        if self.dvt is None:
            await self._create_process_control()
        try:
            from pymobiledevice3.services.dvt.instruments.core_profile_session_tap import CoreProfileSessionTap
        except Exception as exc:
            raise OperatorError(
                code="ios_pymobiledevice_unavailable",
                message="iOS device support is not available. Reinstall the tool package.",
            ) from exc

        time_config = await CoreProfileSessionTap.get_time_config(self.dvt)
        tap = CoreProfileSessionTap(self.dvt, time_config)
        output = io.BytesIO()
        await tap.dump(output, timeout=timeout)
        return summarize_coreprofile_chunk(output.getvalue())

    def read_coreprofile_metadata(self, *, timeout: float = 1.0) -> dict[str, Any]:
        return self._run_async(self._read_coreprofile_metadata(timeout=timeout))

    def read_fps_sample(self) -> dict[str, Any]:
        if self.graphics is None:
            try:
                self._run_async(self._start_graphics())
            except OperatorError:
                raise
            except Exception as exc:
                logger.exception("iOS graphics FPS collector start failed: %s: %s", type(exc).__name__, exc)
                return self._latest_fps_sample
        if self._graphics_iter is None:
            return self._latest_fps_sample
        try:
            sample = _next_service_item(self._graphics_iter, self._run_async)
        except (StopIteration, StopAsyncIteration):
            return self._latest_fps_sample
        fps = _first_number(
            _normalize_mapping(sample),
            "CoreAnimationFramesPerSecond",
            "coreAnimationFramesPerSecond",
            "fps",
            "FPS",
        )
        if fps is not None:
            self._latest_fps_sample = {"fps": fps}
        return self._latest_fps_sample

    def _record_sysmontap_sample(
        self,
        row: Any,
        *,
        process_fields: list[str],
        timestamp: float,
    ) -> None:
        row = _normalize_sysmontap_row(row)
        if row is None:
            return
        total_cpu = _system_cpu_percent(row)
        process_map = self._process_map(row, process_fields)
        previous = self._latest_system_snapshot
        if process_map is None:
            self._latest_system_snapshot = IOSSystemSnapshot(
                app_cpu_percent=previous.app_cpu_percent,
                total_cpu_percent=total_cpu if total_cpu is not None else previous.total_cpu_percent,
                phys_footprint=previous.phys_footprint,
                memory_mb=previous.memory_mb,
            )
            return

        phys_footprint = _first_int(process_map, "physFootprint", "physicalFootprint", "phys_footprint")
        memory_mb = round(phys_footprint / 1024 / 1024, 3) if phys_footprint is not None else None
        app_cpu = _first_number(process_map, "cpuUsage", "cpu_usage", "app_cpu_percent")
        if app_cpu is None:
            app_cpu = self._app_cpu_percent(process_map, timestamp)

        self._latest_system_snapshot = IOSSystemSnapshot(
            app_cpu_percent=app_cpu if app_cpu is not None else previous.app_cpu_percent,
            total_cpu_percent=total_cpu if total_cpu is not None else previous.total_cpu_percent,
            phys_footprint=phys_footprint if phys_footprint is not None else previous.phys_footprint,
            memory_mb=memory_mb if memory_mb is not None else previous.memory_mb,
        )

    def _process_map(self, row: dict[str, Any], process_fields: list[str]) -> dict[str, Any] | None:
        if self._active_pid is None:
            return None
        processes = row.get("Processes")
        if not isinstance(processes, dict):
            return None
        values = processes.get(self._active_pid) or processes.get(str(self._active_pid))
        if values is None:
            return None
        return dict(zip(process_fields, values, strict=False))

    def _app_cpu_percent(self, process_map: dict[str, Any], timestamp: float) -> float | None:
        user = _first_number(process_map, "cpuTotalUser")
        system = _first_number(process_map, "cpuTotalSystem")
        if user is None or system is None:
            return None
        total = user + system
        previous = self._previous_process_cpu
        self._previous_process_cpu = (total, timestamp)
        if previous is None:
            return None
        previous_total, previous_timestamp = previous
        elapsed = timestamp - previous_timestamp
        if elapsed <= 0 or total < previous_total:
            return None
        return round((total - previous_total) / elapsed * 100.0, 3)

    def _map_battery_snapshot(self, payload: dict[str, Any]) -> IOSBatterySnapshot:
        return IOSBatterySnapshot(
            battery_level=_first_int(payload, "CurrentCapacity", "battery_level", "BatteryCurrentCapacity"),
            temperature_c=_battery_temperature_c(payload.get("Temperature")),
        )

    def close(self) -> None:
        services = list(reversed(self._owned_services))
        self._owned_services.clear()
        self.process_control = None
        self.dvt = None
        self.developer_provider = None
        self.sysmontap = None
        self._sysmontap_iter = None
        self.graphics = None
        self._graphics_iter = None
        self.diagnostics = None
        for service in services:
            close = getattr(service, "close", None)
            if close is None and hasattr(service, "__aexit__"):
                result = service.__aexit__(None, None, None)
            elif close is None and hasattr(service, "__exit__"):
                result = service.__exit__(None, None, None)
            elif close is None:
                continue
            else:
                result = close()
            if inspect.isawaitable(result):
                self._run_async(result)
        if self._runner is not None:
            self._runner.close()
            self._runner = None


def _battery_temperature_c(value: Any) -> float | None:
    try:
        temperature_c = float(value) / 10.0 - 273.15
    except (TypeError, ValueError):
        return None
    if not -20.0 <= temperature_c <= 80.0:
        return None
    return round(temperature_c, 2)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _enter_service(service: Any) -> Any:
    if hasattr(service, "__aenter__"):
        return await _maybe_await(service.__aenter__())
    if hasattr(service, "__enter__"):
        return service.__enter__()
    connect = getattr(service, "connect", None)
    if connect is not None:
        await _maybe_await(connect())
    return service


def _iter_service(service: Any) -> Any:
    if hasattr(service, "__aiter__"):
        return service.__aiter__()
    return iter(service)


def _next_service_item(iterator: Any, run_async: Callable[[Awaitable[Any]], Any]) -> Any:
    if hasattr(iterator, "__anext__"):
        return run_async(iterator.__anext__())
    return next(iterator)


async def _get_user_apps(service: Any) -> Any:
    get_apps = getattr(service, "get_apps")
    try:
        return await _maybe_await(get_apps("User"))
    except TypeError:
        return await _maybe_await(get_apps(application_type="User"))


def _normalize_app_payload(apps: Any) -> list[dict[str, Any]]:
    if isinstance(apps, list):
        return [item for item in apps if isinstance(item, dict)]
    if isinstance(apps, dict):
        normalized = []
        for bundle_id, item in apps.items():
            if not isinstance(item, dict):
                continue
            app = dict(item)
            app.setdefault("CFBundleIdentifier", str(bundle_id))
            normalized.append(app)
        return normalized
    return []


def _normalize_mapping(sample: Any) -> dict[str, Any]:
    return sample if isinstance(sample, dict) else {}


def _normalize_sysmontap_row(row: Any) -> dict[str, Any] | None:
    if isinstance(row, dict):
        return row
    if isinstance(row, bytes):
        try:
            payload = plistlib.loads(row)
        except Exception:
            logger.debug("Ignoring undecodable iOS sysmontap bytes row", exc_info=True)
            return None
        return payload if isinstance(payload, dict) else None
    if isinstance(row, str):
        try:
            payload = plistlib.loads(row.encode("utf-8"))
        except Exception:
            logger.debug("Ignoring undecodable iOS sysmontap text row", exc_info=True)
            return None
        return payload if isinstance(payload, dict) else None
    logger.debug("Ignoring unsupported iOS sysmontap row type %s", type(row).__name__)
    return None


def _object_value(obj: Any, *keys: str, default: Any = None) -> Any:
    if obj is None:
        return default
    for key in keys:
        if isinstance(obj, dict) and key in obj:
            return obj[key]
        if hasattr(obj, key):
            return getattr(obj, key)
    return default


def _connection_type(device: Any) -> str:
    raw = _object_value(device, "connection_type", "ConnectionType", default="")
    if raw:
        return str(raw)
    if bool(_object_value(device, "is_usb", default=False)):
        return "USB"
    if bool(_object_value(device, "is_network", default=False)):
        return "Network"
    return "USB"


def _extract_tunnel_address(payload: Any, device_id: str) -> tuple[str, int] | None:
    if isinstance(payload, dict):
        direct = _normalize_tunnel_address(payload.get(device_id))
        if direct is not None:
            return direct
        tunnels = payload.get("tunnels")
        if isinstance(tunnels, list):
            return _extract_tunnel_address(tunnels, device_id)
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            if item.get("udid") == device_id or item.get("identifier") == device_id:
                return _normalize_tunnel_address(item)
    return None


def _normalize_tunnel_address(raw_address: Any) -> tuple[str, int] | None:
    if raw_address is None:
        return None
    if isinstance(raw_address, dict):
        if raw_address.get("userspaceTun") and raw_address.get("userspaceTunPort") is not None:
            return "127.0.0.1", int(raw_address["userspaceTunPort"])
        address = (
            raw_address.get("tunnel-address")
            or raw_address.get("address")
            or raw_address.get("ip")
            or raw_address.get("host")
        )
        port = (
            raw_address.get("tunnel-port")
            or raw_address.get("rsdPort")
            or raw_address.get("port")
        )
        if address and port is not None:
            return str(address), int(port)
    if isinstance(raw_address, (list, tuple)):
        if len(raw_address) == 2 and isinstance(raw_address[0], str):
            return raw_address[0], int(raw_address[1])
        if raw_address and isinstance(raw_address[0], dict):
            return _normalize_tunnel_address(raw_address[0])
    return None


def _first_number(sample: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = sample.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_int(sample: dict[str, Any], *keys: str) -> int | None:
    value = _first_number(sample, *keys)
    if value is None:
        return None
    return int(value)


def _system_cpu_percent(row: dict[str, Any]) -> float | None:
    direct = _first_number(row, "CPUUsage", "cpuUsage", "totalCPU", "total_cpu_percent")
    if direct is not None:
        return direct
    system_cpu = row.get("SystemCPUUsage")
    if not isinstance(system_cpu, dict):
        return None
    total_load = _first_number(system_cpu, "CPU_TotalLoad", "totalLoad", "TotalLoad")
    if total_load is None:
        return None
    cpu_count = _first_number(row, "CPUCount", "cpuCount")
    if cpu_count is None:
        per_cpu = row.get("PerCPUUsage")
        if isinstance(per_cpu, dict):
            cpu_count = float(len(per_cpu))
        elif isinstance(per_cpu, list):
            cpu_count = float(len(per_cpu))
    if cpu_count and cpu_count > 0:
        return round(total_load / cpu_count, 3)
    return round(total_load, 3)


def _map_pymobiledevice_error(exc: Exception, *, phase: str | None = None) -> OperatorError:
    if phase:
        logger.exception(
            "iOS pymobiledevice failure during %s: %s: %s",
            phase,
            type(exc).__name__,
            exc,
        )
    text = str(exc).lower()
    if any(token in text for token in ("win32security", "no module named", "modulenotfounderror", "importerror")):
        return OperatorError(
            code="ios_pymobiledevice_unavailable",
            message="iOS device support is not available. Reinstall the tool package.",
        )
    if any(token in text for token in ("invalidhostid", "pairing", "trust", "lockdown")):
        return OperatorError(
            code="ios_pairing_required",
            message="Unlock the iPhone, trust this computer, and try again.",
        )
    if any(token in text for token in ("invalidservice", "developer", "dvt", "instruments")):
        return OperatorError(
            code="ios_developer_services_unavailable",
            message="iOS developer services are unavailable. Reconnect the iPhone and try again.",
        )
    if any(token in text for token in ("winerror 1231", "network location", "不能访问网络位置")):
        return OperatorError(
            code="ios_tunnel_unavailable",
            message="iOS tunnel is not reachable. Reconnect the iPhone and try again.",
        )
    if any(token in text for token in ("connection", "disconnect", "usbmux", "broken pipe", "connection reset")):
        return OperatorError(
            code="ios_device_disconnected",
            message="iPhone is not connected. Reconnect it and try again.",
        )
    return OperatorError(
        code="ios_pymobiledevice_error",
        message="iOS device communication failed. Reconnect the iPhone and try again.",
    )


_COREPROFILE_ROW = struct.Struct("<QLLQQQQLLQ")


def summarize_coreprofile_chunk(data: bytes, *, target_code: int = 830472984) -> dict[str, Any]:
    event_codes: Counter[int] = Counter()
    row_count = len(data) // _COREPROFILE_ROW.size
    for offset in range(0, row_count * _COREPROFILE_ROW.size, _COREPROFILE_ROW.size):
        _timestamp, code, *_rest = _COREPROFILE_ROW.unpack_from(data, offset)
        event_codes[code] += 1
    return {
        "byte_count": len(data),
        "row_count": row_count,
        "top_event_codes": [
            {"code": code, "count": count}
            for code, count in event_codes.most_common(10)
        ],
        "target_event_count": event_codes[target_code],
    }
