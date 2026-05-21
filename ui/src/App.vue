<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { bridgeApi } from './api'
import MetricChart from './components/MetricChart.vue'
import StatusCard from './components/StatusCard.vue'
import ToolbarPanel from './components/ToolbarPanel.vue'
import { createSessionStore } from './state/sessionStore'

const store = createSessionStore(bridgeApi)
const selectedDeviceId = ref<string | null>(null)
const selectedPackage = ref<string | null>(null)

const metrics = computed(() => store.snapshot?.metrics ?? [])
const xAxis = computed(() => metrics.value.map((item) => item.timestamp.slice(11, 19)))

function metricSeries(field: keyof (typeof metrics.value)[number]) {
  return computed(() => metrics.value.map((item) => item[field] as number | null))
}

const fpsValues = metricSeries('fps')
const frameTimeValues = metricSeries('frame_time_ms')
const appCpuValues = metricSeries('app_cpu_percent')
const totalCpuValues = metricSeries('total_cpu_percent')
const memoryValues = metricSeries('memory_mb')
const temperatureValues = metricSeries('temperature_c')

async function onRefresh() {
  await store.refreshDevices()
}

async function onSelectDevice(deviceId: string) {
  selectedDeviceId.value = deviceId || null
  selectedPackage.value = null
  if (!deviceId) {
    return
  }
  await store.loadApps(deviceId)
}

function onSelectPackage(packageName: string) {
  selectedPackage.value = packageName || null
}

async function onStart() {
  if (!selectedDeviceId.value || !selectedPackage.value) {
    return
  }
  await store.start(selectedDeviceId.value, selectedPackage.value)
}

async function onStop() {
  await store.stop()
}

onMounted(() => {
  void store.refreshDevices()
})
</script>

<template>
  <main class="page">
    <section class="page__hero">
      <div>
        <p class="page__eyebrow">PerfEngine</p>
        <h1>Mobile Performance Monitor</h1>
      </div>
      <p class="page__caption">Collect Android and iOS app performance signals from one desktop workflow.</p>
    </section>

    <ToolbarPanel
      :devices="store.devices"
      :apps="store.apps"
      :selected-device-id="selectedDeviceId"
      :selected-package="selectedPackage"
      :session-phase="store.session.phase"
      :selectors-locked="store.session.selectors_locked"
      @refresh="onRefresh"
      @select-device="onSelectDevice"
      @select-package="onSelectPackage"
      @start="onStart"
      @stop="onStop"
    />

    <StatusCard
      :session="store.session"
      :status="store.snapshot?.status ?? null"
      :error-message="store.errorMessage"
    />

    <section class="charts">
      <MetricChart title="FPS" :x-axis="xAxis" :values="fpsValues" />
      <MetricChart title="Frame Time" :x-axis="xAxis" :values="frameTimeValues" />
      <MetricChart title="App CPU" :x-axis="xAxis" :values="appCpuValues" />
      <MetricChart title="Total CPU" :x-axis="xAxis" :values="totalCpuValues" />
      <MetricChart title="Memory" :x-axis="xAxis" :values="memoryValues" />
      <MetricChart title="Temperature" :x-axis="xAxis" :values="temperatureValues" />
    </section>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: grid;
  gap: 18px;
  padding: 28px;
  background: #f7faf9;
  color: #0f172a;
}

.page__hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: end;
}

.page__hero h1,
.page__hero p {
  margin: 0;
}

.page__eyebrow {
  margin-bottom: 8px;
  color: #0f766e;
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.page__caption {
  max-width: 360px;
  color: #475569;
}

.charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

@media (max-width: 960px) {
  .page {
    padding: 18px;
  }

  .page__hero {
    display: grid;
  }

  .charts {
    grid-template-columns: 1fr;
  }
}
</style>
