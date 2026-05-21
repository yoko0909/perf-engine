## Context

The current product has an Android-only MVP that QA has manually validated and archived through OpenSpec. It uses a Python backend, pywebview bridge, and Vue/Vite UI with a single-session workflow: refresh devices, choose a device, choose an app, start collection, poll a live snapshot, and stop collection.

`Perftool_Demo` proves that iOS collection can run from a Windows desktop host. Its iOS path uses go-ios device discovery, iOS 17+ tunnel handling, `pymobiledevice3`, and Apple DVT/Instruments services to collect app/system metrics. The demo also collects more metrics than the current Android MVP, but this change intentionally targets parity with the current Android surface first.

## Goals / Non-Goals

**Goals:**

- Add iOS as a first-class platform in the existing single-session desktop workflow.
- Keep Android behavior unchanged.
- Discover connected iOS devices from Windows and expose them in the same selector flow as Android devices.
- Load user-installed iOS apps for a selected device.
- Start, stop, and poll one iOS collection session at a time.
- Normalize iOS samples into the existing live chart shape: FPS, frame time, app CPU, total CPU, memory, and temperature.
- Preserve unavailable or unstable iOS metrics as explicit `null` or `unknown` values.

**Non-Goals:**

- Windows app collection.
- iOS report export, import, screenshots, labels, app install/uninstall, or historical replay.
- Exposing iOS-specific GPU, system memory, IO, network, and energy charts in the first UI surface.
- Achieving identical metric口径 where iOS and Android platform APIs define different underlying measurements.

## Decisions

### Decision: Introduce platform-aware providers behind the existing service flow

The backend will keep the existing service-centered model but add a platform dimension to devices and sessions. Device discovery will combine Android and iOS providers into one UI-facing list. App listing and sampling will dispatch to the provider/sampler that matches the selected device platform.

This keeps the desktop workflow stable while preventing iOS connection logic from leaking into the pywebview bridge or Vue components.

Alternatives considered:

- Copy `Perftool_Demo`'s unified `Api` and iOS client structure directly. Rejected because it mixes connection state, cache/report behavior, screenshots, collection, and UI-facing operations in one object.
- Build a separate iOS screen. Rejected because the product goal is cross-platform consistency and Android MVP already validated the one-screen operator workflow.

### Decision: Treat iOS host connectivity as a platform service

iOS support will isolate Windows host requirements into an iOS connection layer. That layer owns device discovery, trusted-device errors, Developer Mode readiness, iOS 17+ tunnel startup/readiness, and DVT service connection creation.

This gives the service layer simple operator-safe outcomes such as "no iOS device detected", "iOS tunnel unavailable", or "iOS developer services unavailable".

The iOS tunnel is a Windows-host local connection service or proxy, not an app installed on the iPhone. Its purpose is to let the desktop tool reach iOS developer services such as Remote Service Discovery and DVT/Instruments, especially for iOS 17+ devices. The product should prepare this tunnel automatically as part of iOS session readiness so QA operators do not need to run separate command-line setup steps.

Alternatives considered:

- Let each sampler start its own tunnel or DVT connection. Rejected because it would make retry behavior inconsistent and hard to explain to operators.
- Require users to start tunnel tools manually before launching the product. Rejected for the MVP because it makes the first iOS workflow too brittle.

### Decision: Bundle the iOS toolchain with the product package

The iOS implementation will not depend on the operator's Windows machine having go-ios, sib, pymobiledevice3 CLI tools, or related executables installed on PATH. The product package should include the iOS host tooling it needs, similar to `Perftool_Demo`'s `asset\\ios` and `asset\\sib` layout, and the backend should resolve tools from product-owned paths.

This makes the QA experience closer to "unpack and run" and reduces environment drift across machines. If a bundled tool is missing, blocked, or incompatible, the app should surface an operator-safe setup error.

Alternatives considered:

- Depend on user-installed tools. Rejected because it creates too many support cases around missing PATH entries, mismatched versions, and Python environment differences.
- Start with external tools and bundle later. Rejected for this change because the target user experience is a directly usable tool package, not a developer-only prototype.

### Decision: Normalize only the Android MVP metric surface for iOS v1

iOS collection may produce more data than the UI shows. The first iOS live snapshot will map the closest available iOS values into the existing `MetricPoint` fields:

- `fps`: iOS FPS collector value.
- `frame_time_ms`: average frame time derived from FPS (`1000 / FPS`) or available frame data when reliable.
- `app_cpu_percent`: target app CPU usage from the iOS system sampler.
- `total_cpu_percent`: system CPU usage from the iOS system sampler.
- `memory_mb`: target app physical footprint when available.
- `temperature_c`: battery temperature when available and unit conversion has been validated.

Metrics without a reliable source or matching口径 will remain `null`; the UI should render them as missing data, not zero.

The current reference口径 from `Perftool_Demo` is:

- FPS comes from the iOS FPS collector, with CoreAnimation FPS as a fallback in the demo.
- Average frame time is derived from FPS rather than guaranteed full per-frame timing.
- App CPU and total CPU come from the iOS system sampler.
- The main iOS memory value maps best to `physFootprint`; resident memory, virtual memory, and `memAnon` are separate iOS-specific views and should not replace the MVP memory chart.
- Battery temperature comes from iOS battery information, but the unit conversion must be verified on real devices before treating it as reliable.
- GPU, system memory, IO, network, energy, and screenshots exist in the demo but are out of the first UI surface.

Alternatives considered:

- Expose the full demo iOS chart set immediately. Rejected because it expands scope before the platform connection and core workflow are proven.
- Force all iOS fields to match Android by deriving approximations. Rejected because it would make the product look more precise than the platform data supports.

### Decision: Keep extended iOS signals in implementation seams, not the MVP UI

The iOS sampler may internally access GPU, network, energy, system memory, and screenshot APIs when that helps validate the integration, but the UI and requirements for this change only depend on the six Android MVP chart groups plus status. Any extra signals should be behind optional internal models or future-ready mapping points.

Alternatives considered:

- Drop all non-MVP iOS code from the reference analysis. Rejected because Demo's extra collectors help identify future extension points.
- Add hidden UI controls for extra metrics. Rejected because hidden or partial controls increase test burden without user-facing value.

### Decision: Use status prompts for missing or delayed iOS metrics

The UI should not silently hide unavailable iOS metric data and should not fill missing values with zero. If iOS data is delayed or only partially available, the status area should explain what is happening while charts render missing values as empty points.

Expected status behavior:

- Waiting for the next iOS sample: show a "waiting for iOS data" style status.
- Some metrics unavailable: show a "partial iOS metrics unavailable" style status while keeping the session running.
- Metric口径 or unit not yet verified: show `unknown` for that field.
- Collection failure: move to interrupted or error state with a clear reason.

Alternatives considered:

- Render blank charts without explanation. Rejected because operators cannot distinguish normal startup delay from a broken collector.
- Fill unavailable metrics with `0`. Rejected because it creates misleading performance data.

## Risks / Trade-offs

- [iOS device trust or Developer Mode blocks collection] -> Surface a recoverable operator message and keep the session non-running.
- [iOS 17+ tunnel startup is slow or fails] -> Treat tunnel readiness as part of iOS preparation with timeout and explicit failure state.
- [Bundled iOS tool assets are missing or incompatible] -> Validate product-owned tool paths before iOS operations and report a clear setup error.
- [DVT/Instruments APIs vary by iOS version] -> Keep collector calls isolated behind adapter methods and allow missing metrics to be `null`.
- [Metric口径 differs from Android] -> Document field mappings and avoid filling missing iOS metrics with fabricated zero values.
- [Manual device validation is required] -> Treat real-device iOS verification as a user-run checklist and capture observed failures or metric differences before considering the change complete.
- [Reference demo code is large and mixed-responsibility] -> Reuse implementation knowledge and focused helper code only where it fits the current provider/sampler boundaries.

## Migration Plan

No data migration is required. The rollout is additive:

1. Add platform-aware models and dispatch while preserving Android behavior.
2. Add bundled iOS tool path resolution, discovery, app listing, connection readiness, and sampler adapters.
3. Update the UI to show iOS devices/apps in the existing selectors and reuse the current chart groups.
4. Validate Android regression behavior and manually verify the iOS Windows-host workflow with at least one trusted iPhone on a machine that does not rely on user-installed iOS tooling.

Rollback is simple: disable or hide the iOS provider and keep the Android MVP flow unchanged.

## Open Questions

- Is battery temperature available and correctly converted across the target iOS versions, or should the first UI label show temperature as unknown until verified?

The iOS version/device verification matrix is intentionally deferred for now. Manual verification will start with the user's available trusted iPhone, and broader matrix decisions can be made after the first end-to-end workflow is working.

## Current True-Device Findings

Manual testing on a connected iPhone has narrowed the remaining work:

- Device discovery works with bundled `ios.exe list --details`, even when go-ios prints an agent/tunnel warning before the device JSON.
- App listing works with bundled `sib.exe app list -u <udid> -j`; this step should not be blocked by tunnel/DDI preparation.
- Start currently reaches the UI running/waiting state, but real iOS metrics are not yet flowing.
- `sib ps` and `sib perfmon` currently fail with `InvalidService`, and `sib mount` fails while trying to download the Developer Disk Image.
- `sib battery` can return raw battery data, but the temperature unit must be validated before mapping it to `temperature_c`.

The next implementation step is therefore not more UI work. It is to solve the iOS Developer Disk Image/DVT service readiness path, then replace the current `IOSClient` collector placeholders with real status, perf, and battery reads.
