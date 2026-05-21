## ADDED Requirements

### Requirement: QA can view Android-aligned live charts during iOS collection
The system SHALL display the same fixed MVP chart groups during an active iOS session as the Android MVP dashboard: FPS, frame time, app CPU, total CPU, memory, and temperature.

#### Scenario: iOS live charts update during an active session
- **WHEN** an iOS collection session is running and new samples are available
- **THEN** the system updates the fixed chart groups on the desktop dashboard without requiring the operator to change screens

#### Scenario: Unavailable iOS metrics remain visibly missing
- **WHEN** an iOS sample does not include a reliable value for one of the fixed chart groups
- **THEN** the system leaves that metric empty or unknown rather than displaying a fabricated zero value

### Requirement: QA can view current iOS device and app test status while collecting
The system SHALL display a status summary for the current iOS device and target application that includes connection state, device identity, screen state when available, target app state, battery when available, temperature when available, and last refresh time.

#### Scenario: Status card shows the current iOS test state
- **WHEN** an iOS device is selected or an iOS session is running
- **THEN** the system shows the current device and app status summary alongside the charts

#### Scenario: Unknown iOS status signals remain explicit
- **WHEN** a required iOS status signal cannot be determined for the selected device
- **THEN** the system shows an explicit unknown status for that field rather than a misleading derived value

### Requirement: iOS runtime interruptions are surfaced as clear collection states
The system SHALL detect common iOS runtime interruptions and present them as clear operator-facing collection states.

#### Scenario: iOS device disconnect interrupts collection
- **WHEN** the connected iOS device disconnects during an active session
- **THEN** the system stops live collection, marks the session as interrupted, and reports that the device disconnected

#### Scenario: Target iOS application exits during collection
- **WHEN** the target iOS application exits or can no longer be observed during an active session
- **THEN** the system stops live collection and reports that the target application exited

#### Scenario: iOS data has not arrived yet
- **WHEN** the iOS session is active but the next live sample is not yet available
- **THEN** the system reports that it is waiting for device data instead of treating the session as failed
