## ADDED Requirements

### Requirement: QA can start a single Android collection session from one screen
The system SHALL allow a QA operator to refresh connected Android devices, select one detected device, load that device's application list, and start collection for one selected application without navigating away from the main desktop screen.

#### Scenario: Selecting a device enables app loading
- **WHEN** the operator selects a detected Android device while the tool is idle
- **THEN** the system loads applications for that device and keeps the operator on the same screen

#### Scenario: Starting a session locks session inputs
- **WHEN** the operator starts collection for a selected Android application
- **THEN** the system marks the session as running, disables device and application selectors, and shows a stop action on the same screen

### Requirement: The session lifecycle stays predictable for QA operators
The system SHALL manage exactly one active Android collection session at a time and SHALL always return the UI to a stable operator state after stop or startup failure.

#### Scenario: Stopping a running session restores setup controls
- **WHEN** the operator stops an active collection session
- **THEN** the system ends the session, preserves the final visible results on screen, and re-enables device and application selection

#### Scenario: Session startup failure returns to idle
- **WHEN** the operator requests collection but the session cannot start
- **THEN** the system returns to a non-running state and allows the operator to retry without restarting the tool

### Requirement: Common setup failures are communicated in operator language
The system SHALL translate setup and control failures into clear operator-facing messages rather than backend command output.

#### Scenario: No Android device is detected
- **WHEN** the operator refreshes devices and no Android device is available
- **THEN** the system reports that no Android device was detected and does not expose raw ADB output

#### Scenario: ADB is unavailable during setup
- **WHEN** the tool cannot communicate with ADB while preparing a session
- **THEN** the system reports that Android device communication is unavailable and keeps the operator in a recoverable non-running state
