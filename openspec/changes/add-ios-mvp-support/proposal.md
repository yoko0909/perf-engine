## Why

The Android MVP is already usable and has validated the one-screen QA workflow. The next product step is to support iOS devices from the same Windows desktop tool so QA can run the same basic performance workflow across mobile platforms before Windows app collection is added later.

## What Changes

- Add iOS device discovery to the existing desktop workflow.
- Allow a QA operator to select an iPhone, load installed user applications, and start or stop one iOS collection session.
- Map iOS live samples into the existing MVP dashboard shape: FPS, frame time, app CPU, total CPU, memory, and temperature.
- Preserve explicit `unknown` or empty metric values when an iOS signal is unavailable or has a different collection口径, instead of deriving misleading data.
- Automatically prepare required Windows-host iOS tunnel connectivity for iOS versions that need it; this is a host-side service, not an app installed on the iPhone.
- Show visible status prompts when iOS data is delayed, partial, unavailable, or unverified.
- Keep iOS-specific extended metrics such as GPU utilization, system memory, IO, network, energy, and screenshots out of the first UI surface.
- Defer Windows collection support to a later change.

## Capabilities

### New Capabilities
- `ios-session-control`: iOS device/app selection and single-session lifecycle from the desktop workflow.
- `ios-live-visibility`: iOS live performance and status visibility using the Android MVP dashboard shape.

### Modified Capabilities

None.

## Impact

- Adds iOS platform provider and sampler modules under the existing backend architecture.
- Introduces bundled iOS host tooling for Windows-to-iPhone connectivity, `pymobiledevice3`/DVT services, and iOS 17+ tunnel handling without relying on user-installed command-line tools.
- Extends the application service and UI bridge to support platform-aware device, app, session, and snapshot data without changing the Android MVP contract.
- Updates the Vue UI to allow platform-aware selection while keeping the first iOS dashboard aligned with the current fixed chart groups.
- Requires user-run real-device validation for iOS-specific connection behavior and metric口径, with results documented before completion.
