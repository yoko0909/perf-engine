import { reactive } from 'vue'

import type { AppInfo, DeviceInfo, LiveSnapshot, SessionState } from '../types'

const defaultSession: SessionState = {
  phase: 'idle',
  selected_device_id: null,
  selected_package: null,
  selectors_locked: false,
  message: '',
  platform: null,
}

export interface SessionApi {
  listDevices: () => Promise<DeviceInfo[]>
  listApps: (deviceId: string) => Promise<AppInfo[]>
  startSession: (deviceId: string, packageName: string) => Promise<SessionState>
  stopSession: () => Promise<SessionState>
  getLiveSnapshot: () => Promise<LiveSnapshot>
}

export function createSessionStore(api: SessionApi) {
  const state = reactive({
    devices: [] as DeviceInfo[],
    apps: [] as AppInfo[],
    session: { ...defaultSession } as SessionState,
    snapshot: null as LiveSnapshot | null,
    errorMessage: '',
    pollTimer: null as ReturnType<typeof window.setInterval> | null,
  })

  function stopPolling() {
    if (state.pollTimer !== null) {
      window.clearInterval(state.pollTimer)
      state.pollTimer = null
    }
  }

  async function refreshDevices() {
    state.devices = await api.listDevices()
    state.errorMessage = state.devices.length === 0 ? 'No supported devices were detected.' : ''
  }

  async function loadApps(deviceId: string) {
    state.apps = await api.listApps(deviceId)
    state.session = {
      ...state.session,
      selected_device_id: deviceId,
      selected_package: null,
      platform: state.devices.find((device) => device.device_id === deviceId)?.platform ?? null,
    }
  }

  async function start(deviceId: string, packageName: string) {
    state.session = {
      ...state.session,
      phase: 'starting',
      selected_device_id: deviceId,
      selected_package: packageName,
      selectors_locked: true,
      message: 'Starting collection.',
    }
    state.errorMessage = ''
    try {
      state.session = await api.startSession(deviceId, packageName)
    } catch (error) {
      state.session = {
        ...state.session,
        phase: 'error',
        selectors_locked: false,
        message: 'Collection could not be started.',
      }
      state.errorMessage = error instanceof Error ? error.message : state.session.message
      return
    }
    state.errorMessage = state.session.phase === 'error' ? state.session.message : ''
    if (state.session.phase === 'running') {
      await pollOnce()
      startPolling()
    }
  }

  async function stop() {
    state.session = await api.stopSession()
    stopPolling()
  }

  async function pollOnce() {
    state.snapshot = await api.getLiveSnapshot()
    state.session = state.snapshot.session
    if (state.session.phase === 'interrupted' || state.session.phase === 'error') {
      state.errorMessage = state.session.message
      stopPolling()
      return
    }
    if (state.session.phase === 'running') {
      state.errorMessage = state.snapshot.status.status_notice || ''
    }
  }

  function startPolling() {
    if (state.pollTimer !== null) {
      return
    }
    state.pollTimer = window.setInterval(() => {
      void pollOnce()
    }, 1000)
  }

  return {
    get devices() {
      return state.devices
    },
    get apps() {
      return state.apps
    },
    get session() {
      return state.session
    },
    get snapshot() {
      return state.snapshot
    },
    get errorMessage() {
      return state.errorMessage
    },
    refreshDevices,
    loadApps,
    start,
    stop,
    pollOnce,
    startPolling,
  }
}
