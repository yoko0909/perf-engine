## ADDED Requirements

### Requirement: QA can view fixed live performance charts during collection
The system SHALL display a fixed live dashboard during an active Android session that includes FPS or frame time, CPU, memory, and temperature or battery chart groups.

#### Scenario: Live charts update during an active session
- **WHEN** an Android collection session is running and new samples are available
- **THEN** the system updates the fixed chart groups on the desktop dashboard without requiring the operator to change screens

#### Scenario: The dashboard remains fixed for the MVP
- **WHEN** the operator uses the MVP dashboard
- **THEN** the system presents the predefined chart groups and does not require custom widget or metric configuration

### Requirement: QA can view current phone and app test status while collecting
The system SHALL display a status summary for the current device and target application that includes connection state, device identity, screen state, target app state, battery, temperature, and last refresh time.

#### Scenario: Status card shows the current test state
- **WHEN** a device is selected or a session is running
- **THEN** the system shows the current device and app status summary alongside the charts

#### Scenario: Unknown device signals remain explicit
- **WHEN** a required phone-state signal cannot be determined for the selected device
- **THEN** the system shows an explicit unknown status for that field rather than a misleading derived value

### Requirement: Runtime interruptions are surfaced as clear collection states
The system SHALL detect common runtime interruptions and present them as clear operator-facing collection states.

#### Scenario: Device disconnect interrupts collection
- **WHEN** the connected Android device disconnects during an active session
- **THEN** the system stops live collection, marks the session as interrupted, and reports that the device disconnected

#### Scenario: Target application exits during collection
- **WHEN** the target application exits or can no longer be observed during an active session
- **THEN** the system stops live collection and reports that the target application exited

#### Scenario: Data has not arrived yet
- **WHEN** the session is active but the next live sample is not yet available
- **THEN** the system reports that it is waiting for device data instead of treating the session as failed
