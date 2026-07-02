## ADDED Requirements

### Requirement: iOS collection prepares developer services before sampling
The system SHALL prepare the selected iPhone for live collection before starting iOS metric collectors.

#### Scenario: Preparing a trusted iPhone
- **WHEN** the operator starts collection for a selected iOS device and target App
- **THEN** the system prepares iOS communication using the project-owned `pymobiledevice3` integration before starting collectors

#### Scenario: iOS 17 or newer requires service readiness
- **WHEN** the selected iPhone requires an iOS 17+ tunnel or remote service discovery path
- **THEN** the system ensures the service path is ready before opening DVT/Instruments collectors

#### Scenario: Developer services are unavailable
- **WHEN** developer services, DVT services, or required image mounting cannot be prepared
- **THEN** the system reports an operator-safe iOS communication error and does not enter a misleading running collection state

### Requirement: iOS target App state is verified before and during collection
The system SHALL verify that the selected iOS target App is running before collection starts and SHALL detect when it exits during collection.

#### Scenario: Target App is running at start
- **WHEN** the selected iOS target App has a running process on the selected iPhone
- **THEN** the system starts iOS collectors using that process identity

#### Scenario: Target App is not running at start
- **WHEN** the selected iOS target App does not have a running process on the selected iPhone
- **THEN** the system reports that the target iOS App is not running and does not start collectors

#### Scenario: Target App exits during collection
- **WHEN** the active iOS target App can no longer be observed while collection is running
- **THEN** the system stops live collection and reports that the target App exited

### Requirement: iOS device disconnection is detected during collection
The system SHALL detect when the selected iPhone disconnects or becomes unreachable during an active collection session.

#### Scenario: iPhone disconnects during collection
- **WHEN** the selected iPhone disconnects or the `pymobiledevice3` service connection becomes unreachable during collection
- **THEN** the system stops live collection and reports that the iPhone disconnected

#### Scenario: Stop cleans up iOS service resources
- **WHEN** the operator stops an active iOS collection session
- **THEN** the system stops all iOS collectors and closes owned `pymobiledevice3` service resources without requiring an app restart
