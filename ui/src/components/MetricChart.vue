<script setup lang="ts">
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  title: string
  xAxis: string[]
  values: Array<number | null>
}>()

const container = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

function render() {
  if (!container.value) {
    return
  }

  chart ??= echarts.init(container.value)
  chart.setOption({
    animation: false,
    title: {
      text: props.title,
      left: 16,
      top: 12,
      textStyle: {
        fontSize: 14,
        color: '#0f172a',
      },
    },
    grid: {
      top: 48,
      left: 48,
      right: 20,
      bottom: 30,
    },
    tooltip: {
      trigger: 'axis',
    },
    xAxis: {
      type: 'category',
      data: props.xAxis,
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: {
          color: '#dde5eb',
        },
      },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        connectNulls: false,
        showSymbol: false,
        lineStyle: {
          width: 2,
          color: '#0f766e',
        },
        areaStyle: {
          color: 'rgba(15, 118, 110, 0.12)',
        },
        data: props.values,
      },
    ],
  })
}

onMounted(render)
watch(() => [props.xAxis, props.values], render, { deep: true })

onBeforeUnmount(() => {
  chart?.dispose()
})
</script>

<template>
  <div ref="container" class="metric-chart"></div>
</template>

<style scoped>
.metric-chart {
  min-height: 250px;
  border: 1px solid #d8dee6;
  border-radius: 18px;
  background: #ffffff;
}
</style>
