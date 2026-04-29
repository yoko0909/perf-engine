<script setup lang="ts">
import type { PhoneStatus, SessionState } from '../types'

defineProps<{
  session: SessionState
  status: PhoneStatus | null
  errorMessage: string
}>()
</script>

<template>
  <section class="status-card">
    <div class="status-card__header">
      <h2>当前状态</h2>
      <p class="status-card__message">
        {{ errorMessage || session.message || session.phase }}
      </p>
    </div>

    <div class="status-card__grid">
      <article>
        <span>设备</span>
        <strong>{{ status?.device_label || '未选择设备' }}</strong>
      </article>
      <article>
        <span>连接</span>
        <strong>{{ status?.connection_state || 'unknown' }}</strong>
      </article>
      <article>
        <span>屏幕</span>
        <strong>{{ status?.screen_state || 'unknown' }}</strong>
      </article>
      <article>
        <span>应用</span>
        <strong>{{ status?.app_state || 'not_selected' }}</strong>
      </article>
      <article>
        <span>电量</span>
        <strong>{{ status?.battery_level ?? '未知' }}</strong>
      </article>
      <article>
        <span>温度</span>
        <strong>{{ status?.temperature_c ?? '未知' }}</strong>
      </article>
      <article>
        <span>最近刷新</span>
        <strong>{{ status?.last_updated_at || '未开始' }}</strong>
      </article>
      <article>
        <span>会话阶段</span>
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
  border-radius: 18px;
  background: linear-gradient(160deg, #ffffff, #f4f8fb);
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
  border-radius: 14px;
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
