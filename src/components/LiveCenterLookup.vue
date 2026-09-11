<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { requestCenters, validateResponse } from '../services/centers'
import type { Center } from '../types'

const centers = ref<Center[]>([])
const busy = ref(false)
const loaded = ref(false)
const error = ref('')
let disposed = false
onBeforeUnmount(() => {
  disposed = true
})

async function lookup() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  loaded.value = false
  centers.value = []
  try {
    const result = validateResponse(await requestCenters('/api/tms/centerList'))
    if (disposed) return
    centers.value = result.resultData
    loaded.value = true
  } catch (cause) {
    if (!disposed)
      error.value = cause instanceof Error ? cause.message : '센터를 조회하지 못했습니다.'
  } finally {
    if (!disposed) busy.value = false
  }
}
</script>

<template>
  <div class="live-center-lookup">
    <div class="lookup-heading">
      <strong>실제 TMS 센터</strong>
      <button type="button" :disabled="busy" @click="lookup">
        {{ busy ? '조회 중…' : '실제 센터 조회' }}
      </button>
    </div>
    <p class="lookup-note">조회 전용입니다. 위 센터와 차량·주문은 목업 배차 데이터입니다.</p>
    <p v-if="error" class="lookup-error" role="alert">{{ error }}</p>
    <div role="status">
      <p v-if="loaded">
        {{
          centers.length ? `${centers.length}개 센터를 조회했습니다.` : '등록된 센터가 없습니다.'
        }}
      </p>
    </div>
    <ul v-if="centers.length" aria-label="실제 TMS 센터 조회 결과">
      <li v-for="item in centers" :key="item.centerId">
        <strong>{{ item.centerName }}</strong>
        <span>{{ item.address }}</span>
        <small>센터 ID: {{ item.centerId }}</small>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.live-center-lookup {
  border-top: 1px solid var(--border);
  padding: 20px;
  font-size: 14px;
  line-height: 1.6;
}
.lookup-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.lookup-heading button {
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 7px 10px;
  color: var(--primary-600);
  background: var(--background);
}
.lookup-heading button:disabled {
  opacity: 0.6;
  cursor: wait;
}
.lookup-note {
  margin-top: 8px;
  color: var(--text-secondary);
}
.lookup-error {
  margin-top: 10px;
  color: #a33e2f;
}
ul {
  list-style: none;
  padding: 0;
  margin-top: 10px;
  max-height: 260px;
  overflow-y: auto;
}
li {
  display: grid;
  gap: 3px;
  padding: 10px 0;
  border-top: 1px solid var(--border);
  overflow-wrap: anywhere;
}
li small {
  color: var(--text-secondary);
}
</style>
