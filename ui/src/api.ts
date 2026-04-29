import type { AppInfo, DeviceInfo, LiveSnapshot, SessionState } from './types'

interface PyWebviewApi {
  list_devices: () => Promise<DeviceInfo[]>
  list_apps: (deviceId: string) => Promise<AppInfo[]>
  start_session: (deviceId: string, packageName: string) => Promise<SessionState>
  stop_session: () => Promise<SessionState>
  get_live_snapshot: () => Promise<LiveSnapshot>
}

declare global {
  interface Window {
    pywebview?: {
      api: PyWebviewApi
    }
  }
}

function getApi(): PyWebviewApi {
  const api = window.pywebview?.api
  if (!api) {
    throw new Error('pywebview api unavailable')
  }
  return api
}

export const bridgeApi = {
  listDevices(): Promise<DeviceInfo[]> {
    return getApi().list_devices()
  },
  listApps(deviceId: string): Promise<AppInfo[]> {
    return getApi().list_apps(deviceId)
  },
  startSession(deviceId: string, packageName: string): Promise<SessionState> {
    return getApi().start_session(deviceId, packageName)
  },
  stopSession(): Promise<SessionState> {
    return getApi().stop_session()
  },
  getLiveSnapshot(): Promise<LiveSnapshot> {
    return getApi().get_live_snapshot()
  },
}
