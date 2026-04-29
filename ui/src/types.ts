export type SessionPhase =
  | 'idle'
  | 'loading_devices'
  | 'loading_apps'
  | 'starting'
  | 'running'
  | 'stopped'
  | 'interrupted'
  | 'error'

export interface DeviceInfo {
  device_id: string
  display_name: string
  connection_type: string
}

export interface AppInfo {
  package_name: string
  display_name: string
  pid: number | null
}

export interface SessionState {
  phase: SessionPhase
  selected_device_id: string | null
  selected_package: string | null
  selectors_locked: boolean
  message: string
}

export interface PhoneStatus {
  connection_state: string
  device_label: string
  screen_state: string
  app_state: string
  battery_level: number | null
  temperature_c: number | null
  last_updated_at: string
}

export interface MetricPoint {
  timestamp: string
  fps: number | null
  frame_time_ms: number | null
  app_cpu_percent: number | null
  total_cpu_percent: number | null
  memory_mb: number | null
  temperature_c: number | null
  battery_level: number | null
}

export interface LiveSnapshot {
  session: SessionState
  status: PhoneStatus
  metrics: MetricPoint[]
}
