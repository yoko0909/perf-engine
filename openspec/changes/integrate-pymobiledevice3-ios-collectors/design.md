## Context

The current iOS MVP backend has working device discovery through bundled `assets/ios/ios.exe list --details`, working App listing through bundled `assets/ios/sib.exe app list -u <udid> -j`, and service/UI plumbing for iOS sessions. The remaining runtime path is still mostly placeholder code: `IOSClient.get_phone_status()` always reports connected/running, collector start/stop are no-ops, and sample reads return empty dictionaries.

`Perftool_Demo` demonstrates that the missing runtime capabilities can be built with `pymobiledevice3` and Apple services: lockdown/usbmux or Remote Service Discovery for device communication, DVT/Instruments for process control and metrics, DiagnosticsService for battery, and AMFI/mobile image mounting for developer service readiness. The project now pins `pymobiledevice3==9.0.0`, so this change can use that dependency directly instead of continuing to rely on `sib perfmon` paths that have failed with `InvalidService` during manual testing.

The implementation must fit the existing desktop MVP boundaries: platform routing remains in `PerfToolService`, iOS behavior remains behind `IOSClient` and `IOSSampler`, and chart data still maps into the existing `MetricPoint` model.

## Current Spike Findings

Validation against `pymobiledevice3==9.0.0` on Windows with a trusted USB iPhone (`ProductVersion=15.0`, `ProductType=iPhone14,5`) found these implementation constraints:

- Windows imports require `pywin32`; without it, importing `pymobiledevice3.lockdown` fails because `win32security` is missing.
- Core APIs are async in 9.0.0. `usbmux.list_devices`, `create_using_usbmux`, service `connect()`, `InstallationProxyService.get_apps()`, `DiagnosticsService.get_battery()`, and DVT calls must be awaited.
- `DvtProvider` is the 9.0.0 DVT entry point; Demo's `DvtSecureSocketProxyService` import path is not available.
- Lockdown, App list, battery, DVT connection, PID lookup, Sysmontap process/system sampling, and Graphics sampling were confirmed to run on the tested device.
- Sysmontap returns process values as lists; the adapter must map them through `fields(sysmon.process_attributes_cls)`. `physFootprint` is available for memory. Direct `cpuUsage` may be `None`, so App CPU likely needs delta calculation from cumulative CPU fields.
- CoreProfile starts and returns raw bytes, but the Demo parser looking for event code `830472984` did not find matching events in the tested sample. FPS/frame time remains a separate spike before production mapping.

## Goals / Non-Goals

**Goals:**
- Add a focused `pymobiledevice3` adapter layer that can connect to a selected iPhone, prepare developer/DVT services, query the target App PID, and read live samples.
- Replace iOS status placeholders with real device connected/disconnected and target App running/exited states.
- Feed the existing iOS sampler with FPS, frame time, App CPU, total CPU, memory, battery level, and temperature when available.
- Preserve operator-safe error handling and recoverable status notices instead of surfacing raw library tracebacks.
- Keep unit tests independent from physical devices by faking the adapter boundary, and keep true-device checks in manual validation docs.

**Non-Goals:**
- Replacing the current `ios.exe` device discovery path.
- Replacing the current `sib.exe` App list path unless implementation testing proves it necessary.
- Adding screenshot UI, syslog browsing, IPA install/uninstall, AFC file transfer, GPU/network/energy charts, or Demo parity beyond the MVP chart/status set.
- Guaranteeing support for every iOS/iPhone combination without manual validation evidence.

## Decisions

1. **Introduce a project-owned `pymobiledevice3` adapter instead of importing the library throughout `IOSClient`.**

   `IOSClient` should depend on a small internal adapter object with methods such as `connect(device_id)`, `prepare_developer_services()`, `get_running_pid(package_name)`, `start_collectors(pid)`, `read_*_sample()`, and `close()`. This keeps third-party API churn isolated and makes tests straightforward. The alternative is to port Demo code directly into `IOSClient`, but that would recreate Demo's broad mixed-responsibility shape in the main project.

   The adapter must own the async/sync boundary. The rest of the current backend is synchronous, so the adapter should run awaited `pymobiledevice3` calls behind a small synchronous facade rather than forcing `PerfToolService`, `BridgeApi`, or UI polling to become async in this change.

2. **Keep command-line tooling for discovery and App listing for now.**

   Discovery and App listing are already verified in the current project. `pymobiledevice3` can list devices and Apps, but switching those paths at the same time as live collection would increase the validation surface without solving the current blocker. The adapter can still use `pymobiledevice3` for target PID lookup after an App is selected.

3. **Prepare DVT services during session begin, not during App list loading.**

   App list loading should remain fast and should not be blocked by Developer Disk Image or DVT readiness. `IOSSampler.begin()` already calls `IOSClient.prepare()`, so the correct place to ensure tunnel, developer mode, image mounting, and DVT service access is session start.

4. **Use long-lived collector objects for streaming metrics, with explicit cleanup.**

   FPS and system samples are stream-oriented in the Demo. The project should create collector instances at `start_collectors()`, read latest samples during `read_*_sample()`, and stop/close them in `stop_collectors()` or on error. This avoids opening a new DVT session on every polling tick.

5. **Map only verified fields into `MetricPoint`; leave unavailable values null.**

   Existing `normalize_ios_metric_point()` already preserves missing metrics as `None`. The adapter should normalize raw `pymobiledevice3` collector output into dictionaries using stable project field names such as `fps`, `frame_time_ms`, `app_cpu_percent`, `total_cpu_percent`, `physFootprint`, `temperature_c`, and `battery_level`.

## Risks / Trade-offs

- [Risk] `pymobiledevice3==9.0.0` APIs differ from Demo's `4.2.3` code paths. → Mitigation: inspect/import version-specific APIs during implementation and wrap them behind the adapter; test adapter behavior with fakes and perform manual true-device validation.
- [Risk] The adapter may deadlock or leak tasks if the async event loop is hidden poorly behind synchronous methods. → Mitigation: keep one explicit adapter-owned loop boundary, test cleanup, and avoid nested `asyncio.run()` inside an already-running loop.
- [Risk] iOS 17+ DVT services may require tunnel/DDI/developer mode sequencing that differs by device. → Mitigation: keep readiness in a dedicated prepare method, return specific operator-safe errors, and document true-device findings.
- [Risk] Streaming collector threads can leak if start fails midway or the device disconnects. → Mitigation: make collector startup transactional, implement idempotent stop/close, and call cleanup on exceptions.
- [Risk] Battery temperature units may be inconsistent or unverified. → Mitigation: do not populate `temperature_c` until unit conversion is verified; keep status notice behavior for missing metrics.
- [Risk] Importing `pymobiledevice3` at module import time can make the app fail if the dependency is missing in a packaged build. → Mitigation: dependency is now declared; still keep imports localized where practical and convert import/setup failures to operator-safe errors.

## Migration Plan

1. Keep the current `ios.exe` and `sib.exe` paths active.
2. Add the adapter and wire it into `IOSClient` behind optional constructor injection so tests can use fakes.
3. Replace placeholder iOS status and collector methods incrementally while preserving current bridge/service APIs.
4. Run Python tests and add focused iOS adapter/client/sampler coverage.
5. Perform manual validation on a trusted iPhone: device refresh, App list, start collection, metrics flow, target App exit, iPhone disconnect, stop cleanup.

Rollback is straightforward: keep `pymobiledevice3` declared but switch `IOSClient` injection back to a no-op/fake adapter, or revert the iOS client changes while leaving discovery and App list behavior untouched.

## Open Questions

- Which `pymobiledevice3==9.0.0` collector API and event parser should provide FPS and frame time, since CoreProfile returns bytes but the Demo event code did not match on the tested iOS 15 device?
- Can `developer_disk_image` bundled through `pymobiledevice3` resolve the DDI preparation issue seen with `sib mount`, or do we need to ship/cache images explicitly?
- Is the observed battery `Temperature` field consistently 0.1 Kelvin across target iOS versions, or should temperature remain unavailable until more devices are validated?
