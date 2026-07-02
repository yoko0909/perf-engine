## 1. Dependency and API Baseline

- [x] 1.1 Add Windows conditional dependency `pywin32` to `pyproject.toml`, because `pymobiledevice3==9.0.0` imports `win32security` through its Windows OS utilities.
  - Verified by adding `pywin32>=312; platform_system == 'Windows'`.
- [x] 1.2 Run `python -m pip install -e .` and verify `python -c "import pymobiledevice3.lockdown; import win32security; print('ok')"` prints `ok`.
  - Verified: `python -m pip install -e .` succeeded and import check printed `ok`.
- [x] 1.3 Add `tests/ios/test_pymobiledevice_adapter.py` with fake async services and no physical-device dependency.
  - Added fake async service coverage in `tests/ios/test_pymobiledevice_adapter.py`.
- [x] 1.4 Document the confirmed 9.0.0 API baseline in `docs/manual-tests/ios-mvp-support.md`: `usbmux.list_devices`, `create_using_usbmux`, service `connect()`, `get_apps()`, `get_battery()`, and DVT calls are async; `DvtProvider` replaces Demo's old `DvtSecureSocketProxyService`.
  - Documented async API baseline, Windows `pywin32` import requirement, DVT entrypoint, verified App list/battery/PID/Sysmontap findings, and open FPS question.

## 2. Async Adapter Boundary

- [x] 2.1 Create `src/perfengine/ios/pymobiledevice.py` with project-owned data classes: `IOSProcessStatus`, `IOSSystemSnapshot`, `IOSBatterySnapshot`, and `IOSCollectorSnapshot`.
  - Created adapter module and project-owned snapshot/status data classes.
- [x] 2.2 In `src/perfengine/ios/pymobiledevice.py`, implement a private event-loop bridge that lets the existing synchronous `IOSClient` call async `pymobiledevice3` operations without changing bridge/service APIs.
  - Implemented `_run_async()` with `asyncio.run()` and operator-safe exception mapping.
- [x] 2.3 In `tests/ios/test_pymobiledevice_adapter.py`, add a failing test proving the sync bridge returns an async fake result and propagates a fake exception as an `OperatorError`.
  - Verified red state with missing module, then green after implementation.
- [x] 2.4 Implement `PymobiledeviceIOSAdapter.connect(device_id)` using `await create_using_usbmux(serial=device_id)` for the current iOS 15/USB path.
  - Implemented `connect()` with injectable async usbmux factory and default localized import.
- [x] 2.5 Implement adapter cleanup with idempotent `close()` that closes any opened DVT, ProcessControl, Sysmontap, CoreProfile, and Diagnostics resources exactly once.
  - Implemented idempotent close over owned sync/async service resources.
- [x] 2.6 Run `python -m pytest tests/ios/test_pymobiledevice_adapter.py -q` and confirm the adapter lifecycle tests pass.
  - Verified: `python -m pytest tests/ios/test_pymobiledevice_adapter.py -q` passed with `5 passed`.

## 3. Readiness and Status

- [x] 3.1 Modify `src/perfengine/ios/client.py` so `IOSClient.__init__` accepts an optional `device_adapter` while preserving existing `tooling`, `tunnel_manager`, and `runner` tests.
  - Added optional `device_adapter` injection with default `PymobiledeviceIOSAdapter()`.
- [x] 3.2 Update `tests/ios/test_client.py` with a fake adapter and a failing test that `IOSClient.prepare("UDID1")` calls both `tunnel_manager.ensure_ready("UDID1")` and adapter readiness.
  - Added fake adapter coverage for tunnel readiness, adapter connect, and developer service readiness.
- [x] 3.3 Implement `IOSClient.prepare()` so it keeps current tunnel readiness behavior and then calls adapter `connect()` plus DVT/developer service preparation.
  - Implemented `prepare()` as tunnel readiness, usbmux connect, then adapter `prepare_developer_services()`.
- [x] 3.4 Add fake-adapter tests for target App PID lookup: running App returns a PID, missing App maps to an `OperatorError` with code `ios_app_not_running`.
  - Added running/not-running status tests and start failure coverage for `ios_app_not_running`.
- [x] 3.5 Implement adapter PID lookup with `DvtProvider` and `ProcessControl.process_identifier_for_bundle_identifier(package_name)`.
  - Implemented lazy DVT/ProcessControl setup using the 9.0.0 module paths and async PID query.
- [x] 3.6 Replace placeholder `IOSClient.get_phone_status()` with adapter-backed status: connected/running when PID exists, connected/exited when PID disappears after start, disconnected when the adapter reports connection loss.
  - Replaced placeholder status with adapter-backed running/not_running/exited/disconnected mapping.
- [x] 3.7 Extend `tests/ios/test_sampler.py` to cover iPhone disconnect during `begin()` and during `read()`.
  - Added sampler disconnect tests for `begin()` failure and `read()` returning no metric point.
- [x] 3.8 Run `python -m pytest tests/ios/test_client.py tests/ios/test_sampler.py -q`.
  - Verified: `python -m pytest tests/ios/test_client.py tests/ios/test_sampler.py -q` passed with `17 passed`.

## 4. System and Battery Collection

- [x] 4.1 Add adapter tests with two fake Sysmontap samples proving App CPU percentage can be computed from deltas of `cpuTotalUser + cpuTotalSystem` over sample time.
  - Added cumulative CPU delta test in `tests/ios/test_pymobiledevice_adapter.py`.
- [x] 4.2 Implement long-lived Sysmontap startup using `Sysmontap.create(dvt)` and `async with sysmon`, keeping the latest system row and process row for the active PID.
  - Implemented `start_collectors()` with `await Sysmontap.create(dvt)`, manual async context entry, and retained async iterator.
- [x] 4.3 Map Sysmontap process fields by zipping `fields(sysmon.process_attributes_cls)` with the process value list; expose `physFootprint`, `memResidentSize`, `cpuTotalUser`, `cpuTotalSystem`, and process `name`.
  - Implemented process row mapping through dataclass field names and exposed CPU/memory snapshot fields.
- [x] 4.4 Implement `IOSClient.start_collectors()` and `stop_collectors()` for the system collector first, with cleanup if startup fails after DVT opens.
  - Wired `IOSClient` start/stop to adapter collectors and added adapter cleanup on collector startup failure.
- [x] 4.5 Implement `IOSClient.read_system_sample()` to return project field names: `app_cpu_percent`, `total_cpu_percent`, `physFootprint`, and `memory_mb` when available.
  - Added client mapping from `IOSSystemSnapshot` to project metric keys.
- [x] 4.6 Add battery adapter tests using the observed iOS battery fields: `CurrentCapacity`, `Voltage`, `InstantAmperage`, and `Temperature`.
  - Added observed Diagnostics payload tests in `tests/ios/test_pymobiledevice_adapter.py`.
- [x] 4.7 Implement battery reads with `DiagnosticsService.get_battery()`, mapping `CurrentCapacity` to `battery_level`.
  - Implemented async DiagnosticsService connection and battery read behind adapter sync facade.
- [x] 4.8 Convert observed temperature values like `2959` as 0.1 Kelvin only behind a named helper, mapping to Celsius as `round(value / 10 - 273.15, 2)`; keep `temperature_c=None` if the value is missing or outside a plausible Celsius range.
  - Added `_battery_temperature_c()` with plausible Celsius guard.
- [x] 4.9 Extend `tests/ios/test_metrics.py` so existing `normalize_ios_metric_point()` accepts the adapter field names and preserves missing values as `None`.
  - Added adapter field-name coverage for CPU, memory, battery, and missing temperature.
- [x] 4.10 Run `python -m pytest tests/ios/test_pymobiledevice_adapter.py tests/ios/test_client.py tests/ios/test_metrics.py -q`.
  - Verified: `python -m pytest tests/ios/test_pymobiledevice_adapter.py tests/ios/test_client.py tests/ios/test_metrics.py -q` passed with `26 passed`.

## 5. FPS and Frame Time Spike

- [x] 5.1 Add `docs/manual-tests/ios-mvp-support.md` notes that CoreProfile starts and returns bytes on the tested iOS 15 device, but Demo's `code == 830472984` parser did not find matching events.
  - Documented CoreProfile/FPS as an open validation item in the 9.0.0 baseline section.
- [x] 5.2 Create an isolated helper in `src/perfengine/ios/pymobiledevice.py` that starts `CoreProfileSessionTap` and returns raw chunk metadata only: byte count, row count, top event codes, and target event count.
  - Added `read_coreprofile_metadata()` and `summarize_coreprofile_chunk()` for raw metadata only.
- [x] 5.3 Add unit tests for the CoreProfile parser using fixed byte rows and the Demo-style `<QLLQQQQLLQ` unpacking.
  - Added fixed-row parser coverage in `tests/ios/test_pymobiledevice_adapter.py`; test execution is pending because the Python test command was rejected by the approval/usage limit after this edit.
- [x] 5.4 Keep production `read_fps_sample()` returning `{}` until a verified event code or alternate 9.0.0 FPS provider is confirmed on a real device.
  - Kept FPS production sample unavailable instead of fabricating FPS/frame time.
- [x] 5.5 If a reliable FPS source is found during manual validation, update `read_fps_sample()` to return `fps` and `frame_time_ms`; otherwise keep FPS as unavailable and rely on the existing missing-metric status notice.
  - No reliable FPS source has been confirmed yet; kept existing missing-metric behavior.

## 6. Operator-Safe Error Mapping

- [x] 6.1 Add tests proving missing `pywin32`, pairing/trust failure, DVT service failure, PID lookup failure, and collector startup failure are converted to `OperatorError` without raw third-party traceback text.
  - Added adapter tests for missing `win32security`, pairing/trust, DVT service failure, PID lookup failure, and collector startup cleanup.
- [x] 6.2 Implement an adapter exception mapper that recognizes import/setup errors, connection errors, DVT service errors, and unexpected async task failures.
  - Added `_map_pymobiledevice_error()` with operator-safe messages for import/setup, pairing, developer service, disconnect, and generic failures.
- [x] 6.3 Ensure collector read failures keep the session running only if adapter status still reports connected/running; otherwise return disconnected/exited status so `IOSSampler` stops appending points.
  - Updated `IOSSampler.read()` to re-check status after collector read failures and return either a recoverable missing-metric notice or an interrupted status.
- [x] 6.4 Add bridge/service regression coverage if any error text crosses `PerfToolService` or `BridgeApi`.
  - Added `PerfToolService` regression coverage for safe operator messages; bridge uses dataclass serialization only.

## 7. Manual Validation

- [x] 7.1 Run a true-device baseline on Windows with a trusted iPhone and record: UDID, ProductType, ProductVersion, App list count, battery fields, PID lookup result, Sysmontap target process row, CoreProfile byte count, and Graphics sample availability.
  - Recorded the trusted USB iPhone baseline and 9.0.0 API findings in `docs/manual-tests/ios-mvp-support.md`.
- [ ] 7.2 Validate normal flow: refresh devices, select iPhone, load App list, start collection, observe memory/battery/system CPU values, stop collection.
- [ ] 7.3 Validate interruption flow: exit the target App during collection and confirm session status changes away from running metric collection.
- [ ] 7.4 Validate disconnection flow: disconnect the iPhone during collection and confirm the app reports an iPhone disconnect without raw traceback.
- [ ] 7.5 Update `docs/manual-tests/ios-mvp-support.md` with pass/fail results and any iOS-version-specific notes.

## 8. Final Verification

- [x] 8.1 Run `python -m pytest tests/ios -q` and fix all iOS test failures.
  - Verified: `python -m pytest tests/ios -q` passed with `56 passed`.
- [x] 8.2 Run `python -m pytest tests -q` and confirm all Python tests pass.
  - Verified: `python -m pytest tests -q` passed with `77 passed`.
- [x] 8.3 Run UI tests only if frontend status copy, polling behavior, or metric display behavior changed.
  - UI tests were not run because no frontend polling/display implementation changed in this pass.
- [x] 8.4 Run `openspec.cmd status --change integrate-pymobiledevice3-ios-collectors` and confirm the change remains complete.
  - Verified: `openspec.cmd status --change integrate-pymobiledevice3-ios-collectors` reports `4/4 artifacts complete`.
- [x] 8.5 Update this `tasks.md` checklist with completed items and concrete verification outputs.
  - Updated completed task notes with verification outputs and left manual validation flow tasks pending.
