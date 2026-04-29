## Why

QA needs a simple Android desktop tool that shows live performance data without requiring command-line workflows or deep technical knowledge. The current workspace only has a reference product, so this change defines the MVP contract for building an internal-use replacement with a predictable operator flow.

## What Changes

- Introduce an Android-only desktop MVP for QA with a single-screen workflow for refreshing devices, selecting an application, and starting or stopping one active collection session.
- Add a layered architecture that separates Android collection logic, application service orchestration, and desktop UI concerns.
- Display a fixed live dashboard with FPS/frame time, CPU, memory, and temperature or battery charts plus current device and app status.
- Surface operator-facing runtime states and common failure feedback such as missing device, disconnected device, exited app, and ADB communication failure.

## Capabilities

### New Capabilities
- `android-session-control`: Manage one Android device and one target application through a stable desktop session lifecycle for QA operators.
- `android-live-visibility`: Show fixed live charts and phone status needed to understand whether the device is currently in a valid test state.

### Modified Capabilities

None.

## Impact

- Adds new change artifacts for the Android QA desktop MVP.
- Affects planned backend modules for ADB access, Android sampling, shared session models, and application service orchestration.
- Affects planned desktop UI modules for pywebview bridging, Vue-based controls, status cards, and ECharts rendering.
- Introduces verification scope for session-state handling, snapshot formatting, and manual Android device scenarios.
