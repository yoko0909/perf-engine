import { afterEach, describe, expect, it, vi } from 'vitest'

import type { LiveSnapshot, SessionState } from '../types'
import { createSessionStore } from './sessionStore'

const runningSession: SessionState = {
  phase: 'running',
  selected_device_id: 'SERIAL1',
  selected_package: 'com.demo.app',
  selectors_locked: true,
  message: '采集中',
}

const snapshot: LiveSnapshot = {
  session: runningSession,
  status: {
    connection_state: 'connected',
    device_label: 'Pixel 8',
    screen_state: 'on',
    app_state: 'running',
    battery_level: 88,
    temperature_c: 33.5,
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
        message: '已停止',
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
})
