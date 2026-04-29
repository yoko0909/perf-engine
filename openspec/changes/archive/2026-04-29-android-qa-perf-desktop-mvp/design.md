## Context

The project currently contains only OpenSpec metadata plus a symlinked reference implementation in `Perftool_Demo`. The reference product proves the general product shape, but it also mixes platform logic, session state, and UI concerns too tightly for a clean MVP restart. This change focuses on an Android-only internal prototype for QA users, where the fastest path to value is a simple desktop flow rather than a broad cross-platform architecture.

The MVP is intentionally constrained to one device, one application, and one active session at a time. The design must optimize for predictable operator behavior, straightforward state recovery, and a low-friction local development setup on Windows machines that already have Python and ADB available.

## Goals / Non-Goals

**Goals:**

- Provide a one-screen desktop workflow for QA to refresh devices, choose an app, and start or stop a single Android session.
- Keep UI logic thin by routing all operations through an application service layer with explicit session states.
- Present live snapshots that combine chart data and phone status in one payload the UI can poll on a fixed interval.
- Make common failures understandable and recoverable without exposing backend internals to operators.

**Non-Goals:**

- Multi-device or multi-application collection.
- Packaging and installer-quality distribution.
- iOS or Windows support.
- Historical session management, report export, screenshot timelines, or configurable dashboards.
- Complex streaming infrastructure such as WebSocket subscriptions.

## Decisions

### Decision: Use a three-layer MVP architecture

The implementation will be split into:

- An `android` collection layer for ADB access, app discovery, process status, and metric sampling.
- An `app` service layer that owns the single-session state machine, command validation, and UI-facing data models.
- A `ui` layer that only issues commands and renders returned state.

This keeps Android-specific collection details out of the UI and prevents the pywebview bridge from becoming the real source of business logic.

Alternatives considered:

- Copy the reference tool's single-process structure directly. Rejected because it would speed up the first screen but make later changes harder to isolate.
- Build a local HTTP service from day one. Rejected for MVP because it adds process and deployment complexity before the product flow is proven.

### Decision: Use Python + pywebview + Vue 3 + ECharts

Python is the best fit for the backend because it integrates well with ADB process execution, local state handling, and quick iteration. `pywebview` is sufficient for an internal desktop shell without pulling in Electron complexity. Vue 3 plus ECharts provides a simple and familiar way to build the single-screen QA dashboard.

Alternatives considered:

- Electron or Tauri desktop shells. Rejected for MVP because they increase setup and packaging overhead without solving the main product risk.
- A pure terminal UI. Rejected because the goal is operator simplicity and immediate visual feedback.

### Decision: Poll a unified live snapshot once per second

The UI will call a single method such as `get_live_snapshot()` on a fixed interval while a session is active. That snapshot will include session state, device state, app state, latest metric values, chart points, and the latest update timestamp.

This makes UI refresh logic straightforward and keeps failure handling centralized in the service layer.

Alternatives considered:

- Push updates over WebSocket or event subscriptions. Rejected for MVP because it adds bidirectional state complexity with little user-facing benefit.
- Separate polling calls for charts and device status. Rejected because it creates avoidable inconsistency between what the charts show and what the status card reports.

### Decision: Fix the MVP dashboard scope

The first version will always show the same operator flow and the same chart groups:

- FPS and frame time
- App CPU and total CPU
- App memory
- Temperature or battery

The status card will show connection state, device identity, screen state, target app state, battery, temperature, and last refresh time. Fixed scope is necessary to keep the UI obvious for QA and avoid early customization debt.

Alternatives considered:

- Allow custom metric selection or rearrangeable widgets. Rejected because it undermines the simplicity goal and expands test surface too early.

## Risks / Trade-offs

- [ADB behavior differs across devices] -> Wrap raw commands in dedicated Android provider modules and normalize failures into operator-safe error states.
- [Polling may surface temporary empty samples] -> Distinguish "waiting for device data" from terminal failures and keep the last stable UI state visible.
- [pywebview bridge can accumulate UI-driven state] -> Keep all session state in the service layer and restrict the bridge to command forwarding and data return.
- [Phone status signals such as lock-screen state may vary by OEM] -> Define a fallback "unknown" value in the shared model and avoid blocking the session unless collection is truly interrupted.
- [A fixed dashboard may hide deeper root causes] -> Treat this MVP as a QA workflow tool, not a full performance investigation suite, and defer advanced metrics to follow-up changes.

## Migration Plan

No data migration is required because the workspace does not yet contain an existing implementation of this product.

Implementation rollout should follow three internal milestones:

1. Build the layered project skeleton and the single-session state model.
2. Add Android device, app, and sampling support plus the unified live snapshot API.
3. Build the desktop UI and validate the main QA flow against real devices.

Rollback is simple: if the MVP is unstable, stop using the new tool and continue relying on the reference product while the change remains unshipped.

## Open Questions

- Should the first release use `dumpsys gfxinfo`, `SurfaceFlinger`, or an existing on-device helper for FPS and frame time collection?
- Which device-state signal is the most reliable cross-device indicator for `screen_state` in the MVP model?

These questions are implementation-level and do not block artifact creation because the capability contract stays the same either way.
