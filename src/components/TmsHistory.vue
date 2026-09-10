<script setup lang="ts">
import { tmsLogs } from '../stores/tms'
</script>
<template>
  <section class="tms-history">
    <h2>
      물류 API 실행 기록 <span>{{ tmsLogs.length }}</span>
    </h2>
    <p v-if="!tmsLogs.length" class="history-empty">
      차량·배송지·배차 API를 실행하면 요청과 응답이 여기에 표시됩니다.
    </p>
    <details v-for="log in tmsLogs" :key="log.id">
      <summary>
        <span :class="['result-status', log.status]">{{
          log.status === 'success' ? '완료' : log.status === 'pending' ? '처리 중' : '실패'
        }}</span>
        {{ log.title }} <small>{{ log.time }} · {{ log.duration }}ms</small>
      </summary>
      <h3>{{ log.method }} {{ log.path }} · 요청</h3>
      <pre>{{ JSON.stringify(log.request, null, 2) }}</pre>
      <h3>응답</h3>
      <pre>{{ JSON.stringify(log.response, null, 2) }}</pre>
    </details>
  </section>
</template>
<style scoped>
.tms-history {
  background: white;
  border-radius: 24px;
  padding: 32px;
  margin-top: 24px;
  min-width: 0;
}
h2 {
  margin: 0 0 24px;
  font-size: 22px;
  font-weight: 500;
}
h2 span {
  font-size: 14px;
  color: var(--ocean);
  margin-left: 10px;
}
h3 {
  font-size: 13px;
  font-weight: 500;
  margin-top: 22px;
}
details {
  border-top: 1px solid var(--line);
  padding: 20px 0;
}
summary {
  cursor: pointer;
  font-size: 13px;
  line-height: 2;
}
small {
  color: var(--muted);
  font-size: 11px;
  margin-left: 12px;
}
.result-status {
  color: var(--ocean);
  background: var(--ocean-light);
  border-radius: 8px;
  padding: 5px 9px;
  font-size: 11px;
}
.result-status.error {
  color: #a04432;
  background: #fff0e9;
}
.result-status.pending {
  color: #836918;
  background: #fff6df;
}
pre {
  background: #f0f6f7;
  padding: 20px;
  border-radius: 12px;
  font-size: 12px;
  line-height: 1.8;
  max-height: 500px;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.history-empty {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.8;
}
@media (max-width: 480px) {
  .tms-history {
    padding: 24px 18px;
  }
}
</style>
