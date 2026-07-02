import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ToolbarPanel from './ToolbarPanel.vue'

describe('ToolbarPanel', () => {
  it('disables selectors while running and shows the stop button', () => {
    const wrapper = mount(ToolbarPanel, {
      props: {
        devices: [
          {
            device_id: 'SERIAL1',
            display_name: 'Pixel 8',
            connection_type: 'usb',
            platform: 'android',
            os_version: null,
          },
        ],
        apps: [{ package_name: 'com.demo.app', display_name: 'com.demo.app', pid: null, platform: 'android' }],
        selectedDeviceId: 'SERIAL1',
        selectedPackage: 'com.demo.app',
        sessionPhase: 'running',
        selectorsLocked: true,
      },
    })

    const selects = wrapper.findAll('select')

    expect(selects[0].attributes('disabled')).toBeDefined()
    expect(selects[1].attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Stop')
  })

  it('shows platform labels for android and ios devices', () => {
    const wrapper = mount(ToolbarPanel, {
      props: {
        devices: [
          {
            device_id: 'SERIAL1',
            display_name: 'Pixel 8',
            connection_type: 'usb',
            platform: 'android',
            os_version: null,
          },
          {
            device_id: 'UDID1',
            display_name: 'QA iPhone',
            connection_type: 'usb',
            platform: 'ios',
            os_version: '15.0',
          },
        ],
        apps: [],
        selectedDeviceId: null,
        selectedPackage: null,
        sessionPhase: 'idle',
        selectorsLocked: false,
      },
    })

    expect(wrapper.text()).toContain('[android] Pixel 8')
    expect(wrapper.text()).toContain('[ios] QA iPhone')
  })
})
