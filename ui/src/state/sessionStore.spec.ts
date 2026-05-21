import { afterEach, describe, expect, it, vi } from 'vitest'

import type { LiveSnapshot, SessionState } from '../types'
import { createSessionStore } from './sessionStore'

const runningSession: SessionState = {
  phase: 'running',
  selected_device_id: 'SERIAL1',
  selected_package: 'com.demo.app',
  selectors_locked: true,
  message: 'Collection is running.',
  platform: 'android',
}

const snapshot: LiveSnapshot = {
  session: runningSession,
  status: {
    platform: 'android',
    connection_state: 'connected',
    device_label: 'Pixel 8',
    screen_state: 'on',
    app_state: 'running',
    battery_level: 88,
    temperature_c: 33.5,
    status_notice: '',
    last_updated_at: '2026-04-24T00:00:00Z',
  },
  metrics: [],
}

describe('createSessionStore', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('locks selectors and refreshes snapshot after start', async () => {
    vi.useFakeTimers()
    const api = {
      listDevices: vi.fn().mockResolvedValue([]),
      listApps: vi.fn().mockResolvedValue([]),
      startSession: vi.fn().mockResolvedValue(runningSession),
      stopSession: vi.fn().mockResolvedValue({
        ...runningSession,
        phase: 'stopped',
        selectors_locked: false,
        message: 'Collection stopped.',
      }),
      getLiveSnapshot: vi.fn().mockResolvedValue(snapshot),
    }
    const store = createSessionStore(api)

    await store.start('SERIAL1', 'com.demo.app')

    expect(store.session.selectors_locked).toBe(true)
    expect(store.snapshot?.status.device_label).toBe('Pixel 8')
    expect(api.getLiveSnapshot).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(1000)

    expect(api.getLiveSnapshot).toHaveBeenCalledTimes(2)
  })

  it('keeps polling and displays status notice when iOS metrics are partially unavailable', async () => {
    vi.useFakeTimers()
    const iosSnapshot: LiveSnapshot = {
      session: {
        ...runningSession,
        selected_device_id: 'UDID1',
        selected_package: 'com.example.app',
        platform: 'ios',
      },
      status: {
        platform: 'ios',
        connection_state: 'connected',
        device_label: 'QA iPhone',
        screen_state: 'on',
        app_state: 'running',
        battery_level: null,
        temperature_c: null,
        status_notice: 'Some iOS metrics are unavailable.',
        last_updated_at: '2026-05-07T00:00:00Z',
      },
      metrics: [
        {
          timestamp: '2026-05-07T00:00:00Z',
          fps: 55,
          frame_time_ms: 18.18,
          app_cpu_percent: null,
          total_cpu_percent: null,
          memory_mb: null,
          temperature_c: null,
          battery_level: null,
        },
      ],
    }
    const api = {
      listDevices: vi.fn().mockResolvedValue([]),
      listApps: vi.fn().mockResolvedValue([]),
      startSession: vi.fn().mockResolvedValue(iosSnapshot.session),
      stopSession: vi.fn().mockResolvedValue({ ...iosSnapshot.session, phase: 'stopped' }),
      getLiveSnapshot: vi.fn().mockResolvedValue(iosSnapshot),
    }
    const store = createSessionStore(api)

    await store.start('UDID1', 'com.example.app')

    expect(store.errorMessage).toBe('Some iOS metrics are unavailable.')

    await vi.advanceTimersByTimeAsync(1000)

    expect(api.getLiveSnapshot).toHaveBeenCalledTimes(2)
  })

  it('shows an error when start request rejects', async () => {
    const api = {
      listDevices: vi.fn().mockResolvedValue([]),
      listApps: vi.fn().mockResolvedValue([]),
      startSession: vi.fn().mockRejectedValue(new Error('iOS tunnel could not be started.')),
      stopSession: vi.fn().mockResolvedValue({ ...runningSession, phase: 'stopped' }),
      getLiveSnapshot: vi.fn().mockResolvedValue(snapshot),
    }
    const store = createSessionStore(api)

    await store.start('UDID1', 'com.example.app')

    expect(store.session.phase).toBe('error')
    expect(store.session.selectors_locked).toBe(false)
    expect(store.errorMessage).toBe('iOS tunnel could not be started.')
  })
})
