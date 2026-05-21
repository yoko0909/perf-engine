<script setup lang="ts">
import { computed } from 'vue'

import type { PhoneStatus, SessionState } from '../types'

const props = defineProps<{
  session: SessionState
  status: PhoneStatus | null
  errorMessage: string
}>()

const message = computed(() => {
  return props.errorMessage || props.status?.status_notice || props.session.message || props.session.phase
})
</script>

<template>
  <section class="status-card">
    <div class="status-card__header">
      <h2>Session Status</h2>
      <p class="status-card__message">
        {{ message }}
      </p>
    </div>

    <div class="status-card__grid">
      <article>
        <span>Device</span>
        <strong>{{ status?.device_label || 'No device selected' }}</strong>
      </article>
      <article>
        <span>Connection</span>
        <strong>{{ status?.connection_state || 'unknown' }}</strong>
      </article>
      <article>
        <span>Screen</span>
        <strong>{{ status?.screen_state || 'unknown' }}</strong>
      </article>
      <article>
        <span>App</span>
        <strong>{{ status?.app_state || 'not_selected' }}</strong>
      </article>
      <article>
        <span>Battery</span>
        <strong>{{ status?.battery_level ?? 'unknown' }}</strong>
      </article>
      <article>
        <span>Temperature</span>
        <strong>{{ status?.temperature_c ?? 'unknown' }}</strong>
      </article>
      <article>
        <span>Updated</span>
        <strong>{{ status?.last_updated_at || 'unknown' }}</strong>
      </article>
      <article>
        <span>Phase</span>
        <strong>{{ session.phase }}</strong>
      </article>
    </div>
  </section>
</template>

<style scoped>
.status-card {
  display: grid;
  gap: 18px;
  padding: 20px;
  border: 1px solid #d8dee6;
  border-radius: 8px;
  background: #ffffff;
}

.status-card__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: baseline;
}

.status-card__header h2,
.status-card__header p {
  margin: 0;
}

.status-card__message {
  color: #8b1e3f;
}

.status-card__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.status-card__grid article {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: 8px;
  background: rgba(230, 240, 245, 0.72);
}

.status-card__grid span {
  color: #4f6174;
  font-size: 12px;
}

@media (max-width: 960px) {
  .status-card__header {
    display: grid;
  }

  .status-card__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
