import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ToolbarPanel from './ToolbarPanel.vue'

describe('ToolbarPanel', () => {
  it('disables selectors while running and shows the stop button', () => {
    const wrapper = mount(ToolbarPanel, {
      props: {
        devices: [{ device_id: 'SERIAL1', display_name: 'Pixel 8', connection_type: 'usb' }],
        apps: [{ package_name: 'com.demo.app', display_name: 'com.demo.app', pid: null }],
        selectedDeviceId: 'SERIAL1',
        selectedPackage: 'com.demo.app',
        sessionPhase: 'running',
        selectorsLocked: true,
      },
    })

    const selects = wrapper.findAll('select')

    expect(selects[0].attributes('disabled')).toBeDefined()
    expect(selects[1].attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('停止采集')
  })
})
