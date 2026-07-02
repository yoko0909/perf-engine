## Why

The current iOS flow can discover iPhones and load App lists, but live collection still uses placeholder status and empty samples, so sessions enter a running state without FPS, CPU, memory, battery, or interruption signals. We need to use the newly pinned `pymobiledevice3==9.0.0` dependency to connect to Apple device services directly and complete the missing iOS runtime path.

## What Changes

- Add a `pymobiledevice3`-backed iOS device service layer for trusted-device connection, iOS 17+ service readiness, and DVT/Instruments access.
- Replace placeholder `IOSClient` status methods with real connection, target App running, PID, and disconnect detection.
- Replace placeholder collector methods with real iOS FPS/frame time, system CPU, App CPU, memory, and battery reads.
- Keep current `ios.exe list --details` device discovery and `sib.exe app list -u <udid> -j` App listing unless implementation evidence shows a targeted replacement is safer.
- Surface iOS collector failures as existing operator-safe errors or recoverable status notices instead of raw `pymobiledevice3` exceptions.
- Do not add Demo-only capabilities such as screenshot browsing, syslog UI, IPA install/uninstall, or file transfer in this change.

## Capabilities

### New Capabilities
- `ios-device-readiness`: Covers preparing iOS device communication for live collection, including trusted-device connection, iOS 17+ tunnel readiness, Developer Disk Image/developer service readiness, target App PID lookup, and clear failure states.
- `ios-live-collection`: Covers live iOS sampling for the current MVP chart groups and status model using `pymobiledevice3` services.

### Modified Capabilities

## Impact

- Python dependency: uses `pymobiledevice3==9.0.0`, already added to `pyproject.toml`.
- Backend code: `src/perfengine/ios/client.py`, `src/perfengine/ios/sampler.py`, `src/perfengine/ios/metrics.py`, and likely new focused helper modules under `src/perfengine/ios/`.
- Tests: add unit tests around the `pymobiledevice3` adapter boundary and extend iOS client/sampler tests for real status and collector behavior using fakes.
- Manual validation: requires a Windows host with a trusted iPhone and existing bundled iOS tooling to verify DVT service readiness and metric flow.
