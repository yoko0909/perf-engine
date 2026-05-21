## ADDED Requirements

### Requirement: QA can start a single iOS collection session from the desktop workflow
The system SHALL allow a QA operator on a Windows host to refresh connected iOS devices, select one detected iPhone, load that device's user application list, and start collection for one selected application without navigating away from the main desktop screen.

#### Scenario: Selecting an iOS device enables app loading
- **WHEN** the operator selects a detected iOS device while the tool is idle
- **THEN** the system loads user applications for that device and keeps the operator on the same screen

#### Scenario: Starting an iOS session locks session inputs
- **WHEN** the operator starts collection for a selected iOS application
- **THEN** the system marks the session as running, disables device and application selectors, and shows a stop action on the same screen

### Requirement: iOS session lifecycle stays predictable for QA operators
The system SHALL manage exactly one active collection session at a time across supported platforms and SHALL always return the UI to a stable operator state after iOS stop, startup failure, or preparation failure.

#### Scenario: Stopping a running iOS session restores setup controls
- **WHEN** the operator stops an active iOS collection session
- **THEN** the system ends the session, preserves the final visible results on screen, and re-enables device and application selection

#### Scenario: iOS startup failure returns to idle
- **WHEN** the operator requests iOS collection but the session cannot start
- **THEN** the system returns to a non-running state and allows the operator to retry without restarting the tool

### Requirement: iOS setup failures are communicated in operator language
The system SHALL translate iOS discovery, tunnel, trust, Developer Mode, and DVT service failures into clear operator-facing messages rather than raw command output or tracebacks.

#### Scenario: No iOS device is detected
- **WHEN** the operator refreshes devices and no iOS device is available
- **THEN** the system reports that no iOS device was detected without exposing raw go-ios or pymobiledevice output

#### Scenario: iOS tunnel is unavailable
- **WHEN** the selected iOS device requires a tunnel and the tunnel cannot be prepared
- **THEN** the system reports that iOS device communication is unavailable and keeps the operator in a recoverable non-running state

#### Scenario: iOS developer services are unavailable
- **WHEN** the tool cannot access required iOS developer services for the selected device
- **THEN** the system reports that iOS performance services are unavailable and keeps the operator in a recoverable non-running state
