<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import TmsHistory from './TmsHistory.vue'
import { apiCatalog } from '../services/tms-mock'
import { callTms, sampleRequest } from '../stores/tms'
import type { MockScenario } from '../stores/tms'
const path = ref('/vehicleList')
const operation = computed(() => apiCatalog.find((o) => o.path === path.value)!)
const draft = ref('{}')
const response = ref<unknown>(null)
const busy = ref(false)
const error = ref('')
const scenario = ref<MockScenario>('success')
function loadSample() {
  draft.value = JSON.stringify(sampleRequest(operation.value), null, 2)
  error.value = ''
}
watch(
  path,
  () => {
    loadSample()
    response.value = null
    scenario.value = 'success'
  },
  { immediate: true },
)
async function send() {
  busy.value = true
  error.value = ''
  response.value = null
  try {
    response.value = await callTms(path.value, JSON.parse(draft.value), scenario.value)
  } catch {
    error.value = '유효한 JSON 객체를 입력하세요.'
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <section class="tms-card">
    <div class="tms-section-heading">
      <div>
        <h2>API 샘플 실행</h2>
        <p>센터부터 교차금지선까지, 24개 API를 연결해 살펴보세요.</p>
      </div>
      <span class="tms-count">24 APIs</span>
    </div>
    <label class="tms-label"
      >API 선택<select v-model="path" :disabled="busy">
        <option v-for="op in apiCatalog" :key="op.path" :value="op.path">
          {{ op.title }} · {{ op.method }} {{ op.path }}
        </option>
      </select></label
    >
    <div class="endpoint-line">
      <span>{{ operation.method }}</span
      ><code>{{ operation.path }}</code
      ><a :href="operation.source" target="_blank" rel="noreferrer">공식 명세 ↗</a>
    </div>
    <details class="api-details">
      <summary>요청 필드 · {{ operation.parameters.length }}개</summary>
      <dl>
        <template v-for="p in operation.parameters" :key="p.name"
          ><dt>
            {{ p.name }} <span>{{ p.type }} · {{ p.required ? '필수' : '선택' }}</span>
          </dt>
          <dd>{{ p.description }}</dd></template
        >
      </dl>
      <p v-if="!operation.parameters.length">추가 요청 파라미터가 없습니다.</p>
    </details>
    <form @submit.prevent="send">
      <div class="tms-section-heading compact">
        <label for="api-json">요청 JSON</label
        ><button type="button" :disabled="busy" @click="loadSample">
          현재 데이터로 예제 채우기 ↻
        </button>
      </div>
      <textarea id="api-json" v-model="draft" :disabled="busy" rows="12" spellcheck="false" />
      <div class="tms-toolbar">
        <select v-model="scenario" aria-label="응답 시나리오" :disabled="busy">
          <option value="success">정상 응답</option>
          <option value="unauthorized">인증 오류 · 401</option>
          <option value="timeout">타임아웃</option>
          <option v-if="path.endsWith('List')" value="empty">빈 목록</option></select
        ><button class="tms-primary" :disabled="busy">{{ busy ? '실행 중…' : '목업 실행' }}</button>
      </div>
    </form>
    <p v-if="error" role="alert" class="tms-notice error">{{ error }}</p>
    <div v-if="response" class="api-response" role="status">
      <h3>실행 응답</h3>
      <pre>{{ JSON.stringify(response, null, 2) }}</pre>
    </div>
    <details class="api-details">
      <summary>공식 문서 응답 예제</summary>
      <p v-if="path === '/orderListInsert'">
        이 API의 문서에는 성공 응답 자리에 reqDatas 요청 예제가 기재되어 있습니다. 목업은 등록 완료
        응답을 별도로 반환합니다.
      </p>
      <p v-if="path === '/allocationData'">
        문서의 vehicleList와 vehicleRouteList는 단일 객체 예제입니다. 여러 차량을 표시하기 위해
        목업에서는 배열로 정규화합니다.
      </p>
      <div v-for="(sample, i) in operation.examples" :key="i">
        <h4>{{ sample.status }}</h4>
        <pre>{{ JSON.stringify(sample.value, null, 2) }}</pre>
      </div>
    </details>
    <p class="tms-footnote">
      실제 API 호출 없이 현재 세션의 데이터를 처리합니다. appKey는 필요하지 않습니다. 문서의 배차
      목록 객체는 목업에서 배열로 정규화하며, 처리 중(102)·검증 오류·무결성 검사는 시연용
      규칙입니다.
    </p>
  </section>
  <TmsHistory />
</template>
