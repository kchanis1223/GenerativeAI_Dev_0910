<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { resources } from '../data/logistics'
import { apiCatalog, vehicleTypes } from '../services/tms-mock'
import { callTms, sampleRequest, tmsState } from '../stores/tms'
import type { Resource, TmsPayload, TmsRow } from '../types/tms'
const props = defineProps<{ initial: Resource; fixedResource?: boolean }>()
const resource = ref<Resource>(props.initial)
watch(
  () => props.initial,
  (v) => {
    resource.value = v
  },
)
const query = ref('')
const meta = computed(() => resources[resource.value])
const rows = computed(() =>
  tmsState[resource.value].filter((r) =>
    JSON.stringify(r).toLowerCase().includes(query.value.toLowerCase()),
  ),
)
const mode = ref<'Insert' | 'Update' | 'ListInsert' | null>(null)
const operation = computed(() =>
  apiCatalog.find((o) => o.path === `/${meta.value.prefix}${mode.value}`),
)
const draft = ref<TmsPayload>({})
const bulk = ref('')
const busy = ref(false)
const message = ref('')
const failed = ref(false)
const selected = ref<TmsRow | null>(null)
const deleteId = ref<string | null>(null)
watch(resource, () => {
  mode.value = null
  selected.value = null
  message.value = ''
  query.value = ''
  deleteId.value = null
})
function edit(action: 'Insert' | 'Update' | 'ListInsert', row?: TmsRow) {
  mode.value = action
  message.value = ''
  deleteId.value = null
  const op = operation.value!
  draft.value = row
    ? Object.fromEntries(
        op.parameters.filter((p) => row[p.name] !== undefined).map((p) => [p.name, row[p.name]]),
      )
    : sampleRequest(op)
  bulk.value = JSON.stringify(draft.value, null, 2)
}
async function submit() {
  busy.value = true
  try {
    const data = mode.value === 'ListInsert' ? JSON.parse(bulk.value) : draft.value
    const result = await callTms(operation.value!.path, data)
    failed.value = result.resultCode !== '200'
    message.value = String(result.resultMessage)
    if (!failed.value) {
      mode.value = null
      selected.value = null
    }
  } catch {
    failed.value = true
    message.value = 'JSON 형식을 확인하세요.'
  } finally {
    busy.value = false
  }
}
async function remove(row: TmsRow) {
  busy.value = true
  const result = await callTms(`/${meta.value.prefix}Delete`, {
    [meta.value.id]: row[meta.value.id],
    ...(['vehicles', 'orders'].includes(resource.value) ? { deleteFlag: '2' } : {}),
  })
  failed.value = result.resultCode !== '200'
  message.value = String(result.resultMessage)
  deleteId.value = null
  selected.value = null
  busy.value = false
}
function description(row: TmsRow) {
  if (resource.value === 'vehicles')
    return `${vehicleTypes[row.vehicleType as keyof typeof vehicleTypes]} · ${row.weight} ton / ${row.volume} cbm · ${row.inputYn === '0' ? '투입 제외' : '투입 가능'} · 숙련도 ${row.skillPer}%`
  if (resource.value === 'orders')
    return `${row.deliveryWeight} kg / ${row.deliveryVolume} cbm · 작업 ${row.serviceTime}분 · ${row.address}`
  return String(row.address ?? row.lineData ?? row.code ?? '')
}
</script>
<template>
  <div v-if="!fixedResource" class="resource-tabs" aria-label="데이터 종류">
    <button
      v-for="(item, key) in resources"
      :key="key"
      :class="{ active: resource === key }"
      @click="resource = key"
    >
      {{ item.title }} <span>{{ tmsState[key].length }}</span>
    </button>
  </div>
  <section class="tms-card">
    <div class="tms-section-heading">
      <div>
        <h2>{{ meta.title }}</h2>
        <p>등록한 정보가 배차 요청과 API 탐색에 함께 반영됩니다.</p>
      </div>
      <span class="tms-count">{{ rows.length }}건</span>
    </div>
    <div class="tms-toolbar">
      <input
        v-model="query"
        :aria-label="`${meta.singular} 검색`"
        placeholder="이름, ID, 주소 검색"
      /><button class="tms-primary" :disabled="busy" @click="edit('Insert')">등록</button
      ><button
        v-if="['zones', 'vehicles', 'orders'].includes(resource)"
        class="tms-secondary"
        :disabled="busy"
        @click="edit('ListInsert')"
      >
        일괄 등록
      </button>
    </div>
    <p v-if="message" role="status" :class="['tms-notice', { error: failed }]">{{ message }}</p>
    <form v-if="mode" class="tms-editor" @submit.prevent="submit">
      <h3>
        {{ meta.singular }}
        {{ mode === 'Update' ? '수정' : mode === 'ListInsert' ? '일괄 등록' : '등록' }}
      </h3>
      <template v-if="mode === 'ListInsert'"
        ><p>reqDatas 배열의 모든 항목을 검사한 뒤 함께 등록합니다.</p>
        <textarea
          v-model="bulk"
          aria-label="일괄 등록 JSON"
          rows="16"
          spellcheck="false"
          required
        />
      </template>
      <div v-else class="tms-fields">
        <label v-for="p in operation!.parameters" :key="p.name"
          >{{ p.name }} <span v-if="p.required" class="required">*</span>
          <select v-if="p.name === 'vehicleType'" v-model="draft[p.name]">
            <option v-for="(label, key) in vehicleTypes" :key="key" :value="key">
              {{ label }} · {{ key }}
            </option>
          </select>
          <select v-else-if="p.name === 'zoneCode'" v-model="draft[p.name]">
            <option value="">권역 미지정</option>
            <option v-for="zone in tmsState.zones" :key="zone.code" :value="zone.code">
              {{ zone.name }} · {{ zone.code }}
            </option>
          </select>
          <select v-else-if="p.name === 'inputYn'" v-model="draft[p.name]">
            <option value="1">투입 가능</option>
            <option value="0">투입 제외</option>
          </select>
          <input
            v-else
            v-model="draft[p.name]"
            :required="p.required"
            :readonly="mode === 'Update' && p.name === meta.id"
            :type="['int', 'float', 'double'].includes(p.type) ? 'number' : 'text'"
            :step="p.type === 'int' ? '1' : 'any'"
          />
          <small>{{ p.description }}</small>
        </label>
      </div>
      <div class="tms-actions">
        <button type="button" class="tms-secondary" :disabled="busy" @click="mode = null">
          취소</button
        ><button class="tms-primary" :disabled="busy">{{ busy ? '저장 중…' : '저장' }}</button>
      </div>
    </form>
    <div v-if="!rows.length" class="tms-empty">표시할 {{ meta.singular }} 정보가 없습니다.</div>
    <ul class="tms-records">
      <li v-for="row in rows" :key="row[meta.id]">
        <div>
          <button class="record-name" @click="selected = selected === row ? null : row">
            {{ row[meta.name] || row[meta.id] }}</button
          ><span class="record-id">{{ row[meta.id] }}</span>
          <p>{{ description(row) }}</p>
          <small v-if="row.zoneCode">권역 {{ row.zoneCode }}</small>
        </div>
        <div class="record-actions">
          <button v-if="resource !== 'banLines'" :disabled="busy" @click="edit('Update', row)">
            수정</button
          ><button :disabled="busy" @click="deleteId = String(row[meta.id])">삭제</button>
        </div>
        <div v-if="deleteId === String(row[meta.id])" class="delete-confirm">
          이 목업 항목을 삭제할까요?<button :disabled="busy" @click="remove(row)">삭제 확인</button
          ><button @click="deleteId = null">취소</button>
        </div>
        <pre v-if="selected === row">{{ JSON.stringify(row, null, 2) }}</pre>
      </li>
    </ul>
  </section>
</template>
