## ADDED Requirements

### Requirement: iOS live collection provides MVP chart metrics
The system SHALL collect and publish iOS samples for the existing MVP chart groups when those values are available from `pymobiledevice3` services.

#### Scenario: iOS sample contains live chart values
- **WHEN** an iOS collection session is running and `pymobiledevice3` collectors provide FPS, frame time, CPU, memory, and battery data
- **THEN** the system appends a `MetricPoint` with FPS, frame time, App CPU, total CPU, memory, battery level, and temperature values mapped to the existing chart fields

#### Scenario: Some iOS metrics are unavailable
- **WHEN** an iOS sample omits one or more MVP metric values
- **THEN** the system leaves the unavailable values empty and keeps the session running with a recoverable status notice

#### Scenario: No iOS sample has arrived yet
- **WHEN** the iOS session is active but no collector has produced a usable sample
- **THEN** the system reports that it is waiting for iOS data and does not append a fabricated zero-valued metric point

### Requirement: iOS collectors use stable project field names
The system SHALL translate raw `pymobiledevice3` output into project-owned field names before metric normalization.

#### Scenario: Raw FPS data is normalized
- **WHEN** a `pymobiledevice3` FPS collector returns raw frame or FPS data
- **THEN** the iOS client exposes FPS data using project-owned keys such as `fps` and `frame_time_ms`

#### Scenario: Raw system data is normalized
- **WHEN** a `pymobiledevice3` system collector returns process and device statistics
- **THEN** the iOS client exposes App CPU, total CPU, and memory data using project-owned keys such as `app_cpu_percent`, `total_cpu_percent`, and `physFootprint`

#### Scenario: Raw battery data is normalized
- **WHEN** a `pymobiledevice3` diagnostics or battery service returns battery data
- **THEN** the iOS client exposes battery level and verified temperature data using project-owned keys such as `battery_level` and `temperature_c`

### Requirement: iOS collector failures remain operator-safe
The system SHALL convert expected `pymobiledevice3` connection, service, and collector failures into operator-safe application states or errors.

#### Scenario: Collector startup fails
- **WHEN** an iOS collector cannot be started because a required service is unavailable
- **THEN** the system reports a clear iOS collection startup error without exposing a raw third-party traceback

#### Scenario: Collector read fails after startup
- **WHEN** an iOS collector read fails after collection has started
- **THEN** the system either keeps the session running with a recoverable missing-data notice or interrupts the session with a clear device/app state, depending on whether the device and target App remain reachable
