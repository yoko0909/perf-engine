<script setup lang="ts">
import type { AppInfo, DeviceInfo, SessionPhase } from '../types'

defineProps<{
  devices: DeviceInfo[]
  apps: AppInfo[]
  selectedDeviceId: string | null
  selectedPackage: string | null
  sessionPhase: SessionPhase
  selectorsLocked: boolean
}>()

defineEmits<{
  refresh: []
  selectDevice: [deviceId: string]
  selectPackage: [packageName: string]
  start: []
  stop: []
}>()
</script>

<template>
  <section class="toolbar">
    <button class="toolbar__button" type="button" @click="$emit('refresh')">刷新设备</button>

    <select
      class="toolbar__select"
      :disabled="selectorsLocked"
      :value="selectedDeviceId ?? ''"
      @change="$emit('selectDevice', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">请选择设备</option>
      <option v-for="device in devices" :key="device.device_id" :value="device.device_id">
        {{ device.display_name }} ({{ device.device_id }})
      </option>
    </select>

    <select
      class="toolbar__select"
      :disabled="selectorsLocked || !selectedDeviceId"
      :value="selectedPackage ?? ''"
      @change="$emit('selectPackage', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">请选择应用</option>
      <option v-for="app in apps" :key="app.package_name" :value="app.package_name">
        {{ app.display_name }}
      </option>
    </select>

    <button
      v-if="sessionPhase !== 'running'"
      class="toolbar__button toolbar__button--primary"
      type="button"
      :disabled="!selectedDeviceId || !selectedPackage"
      @click="$emit('start')"
    >
      开始采集
    </button>
    <button
      v-else
      class="toolbar__button toolbar__button--danger"
      type="button"
      @click="$emit('stop')"
    >
      停止采集
    </button>
  </section>
</template>

<style scoped>
.toolbar {
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr) minmax(0, 1fr) 132px;
  gap: 12px;
  align-items: center;
}

.toolbar__button,
.toolbar__select {
  min-height: 42px;
  border-radius: 12px;
  border: 1px solid #c8d1dc;
  background: #ffffff;
  font-size: 14px;
  padding: 0 14px;
}

.toolbar__button {
  cursor: pointer;
}

.toolbar__button--primary {
  background: #0f766e;
  border-color: #0f766e;
  color: #ffffff;
}

.toolbar__button--danger {
  background: #b91c1c;
  border-color: #b91c1c;
  color: #ffffff;
}

@media (max-width: 960px) {
  .toolbar {
    grid-template-columns: 1fr;
  }
}
</style>
