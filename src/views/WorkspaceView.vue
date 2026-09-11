<script setup lang="ts">
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Box,
  Check,
  ChevronRight,
  Database,
  ExternalLink,
  FileJson,
  GitBranch,
  History,
  LoaderCircle,
  MapPin,
  Radio,
  RotateCcw,
  Search,
  Settings2,
  Terminal,
  X,
} from '@lucide/vue'
import TmsHistory from '../components/TmsHistory.vue'
import { centerHistory } from '../stores/center-history'
import PageSteps from '../components/PageSteps.vue'
import WorkspaceHeader from '../components/WorkspaceHeader.vue'
import CenterMap from '../components/CenterMap.vue'
import {
  API_REFERENCE,
  API_URL,
  CenterApiError,
  filterCenters,
  requestCenters,
  validateProxyEndpoint,
  validateResponse,
  wait,
} from '../services/centers'
import type { Center, Connection, RunRecord, Scenario, TraceStep } from '../types'

const route = useRoute()
const router = useRouter()
const activePage = computed<'centers' | 'flow' | 'history'>({
  get: () =>
    route.params.page === 'flow' ? 'flow' : route.params.page === 'history' ? 'history' : 'centers',
  set: (page) => {
    void router.push(page === 'centers' ? '/workspace/centers' : `/workspace/${page}`)
  },
})
const activeSection = ref(0)
const historyFilter = ref('all')
const visibleRecords = computed(() =>
  records.value.filter(
    (record) => historyFilter.value === 'all' || record.status === historyFilter.value,
  ),
)
const pageSections = computed(() =>
  activePage.value === 'flow'
    ? [
        { label: '조회 조건', target: 'lookup' },
        { label: '요청 정보', target: 'request' },
        { label: '응답 확인', target: 'response' },
        { label: '실행 결과', target: 'execution' },
      ]
    : [
        { label: '조회 조건', target: 'lookup' },
        { label: '센터 목록', target: 'results' },
        { label: '센터 상세', target: 'center-detail' },
        { label: '실행 결과', target: 'execution' },
      ],
)
watch(activePage, () => {
  activeSection.value = 0
})
function navigateSection(index: number) {
  activeSection.value = index
  const target = document.getElementById(pageSections.value[index]!.target)
  target?.scrollIntoView({
    behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
    block: 'start',
  })
  target?.focus({ preventScroll: true })
}
const query = ref('')
const region = ref('전체')
const scenario = ref<Scenario>('success')
const connection = ref<Connection>({ mode: 'mock', endpoint: '/api/tms/centerList' })
const draftConnection = ref<Connection>({ ...connection.value })
const settingsOpen = ref(false)
const settingsDialog = ref<HTMLDialogElement | null>(null)
watch(settingsOpen, async (open) => {
  await nextTick()
  if (open) settingsDialog.value?.showModal()
  else settingsDialog.value?.close()
})
const settingsError = ref('')
const running = ref(false)
const centers = ref<Center[]>([])
const selectedId = ref<string | null>(null)
const selected = computed(() => centers.value.find((c) => c.centerId === selectedId.value))
const records = centerHistory
const rawResponse = ref<unknown>(null)
const responseTab = ref<'summary' | 'json'>('summary')
const error = ref('')
const errorCode = ref('')
const lastRun = ref<RunRecord | null>(null)
const toast = ref('')
const steps = ref<TraceStep[]>(createSteps())
const filteredRegions = computed(
  () => new Set(centers.value.map((c) => c.address.split(' ')[0])).size,
)
const completedSteps = computed(() => steps.value.filter((s) => s.status === 'success').length)
const regions = [
  '서울특별시',
  '경기도',
  '인천광역시',
  '부산광역시',
  '대구광역시',
  '광주광역시',
  '대전광역시',
  '울산광역시',
  '세종특별자치시',
  '강원특별자치도',
  '충청북도',
  '충청남도',
  '전북특별자치도',
  '전라남도',
  '경상북도',
  '경상남도',
  '제주특별자치도',
]
const scenarios: { value: Scenario; label: string }[] = [
  { value: 'success', label: '정상 응답' },
  { value: 'empty', label: '빈 목록' },
  { value: 'unauthorized', label: '인증 오류 · 401' },
  { value: 'timeout', label: '타임아웃' },
  { value: 'invalid', label: '응답 형식 오류' },
]
const appliedFilter = computed(() =>
  lastRun.value
    ? [
        lastRun.value.region === '전체' ? '전체 지역' : lastRun.value.region,
        lastRun.value.query ? `“${lastRun.value.query}”` : '전체 센터',
      ].join(' · ')
    : '전체 지역 · 전체 센터',
)
const requestPreview = computed(() => ({
  method: 'GET',
  endpoint: connection.value.mode === 'mock' ? API_URL : connection.value.endpoint,
  mode: connection.value.mode,
  clientFilter: { query: query.value.trim(), region: region.value },
  authentication: '서버에서 appKey 주입 (실제 연결 시)',
}))

function createSteps(): TraceStep[] {
  return [
    { title: '사용자 입력', description: '검색 조건 확인', status: 'pending', detail: '' },
    { title: 'API 호출', description: 'get_center_list', status: 'pending', detail: '' },
    { title: '응답 검증', description: '스키마 · 상태 코드', status: 'pending', detail: '' },
    { title: '데이터 필터링', description: '지역 · 검색어 적용', status: 'pending', detail: '' },
    { title: '결과 표시', description: '목록 · 위치 · 상세', status: 'pending', detail: '' },
  ]
}
function notify(message: string) {
  toast.value = message
  setTimeout(() => {
    if (toast.value === message) toast.value = ''
  }, 3500)
}
function openSettings() {
  draftConnection.value = { ...connection.value }
  settingsError.value = ''
  settingsOpen.value = true
}
function saveSettings() {
  try {
    if (draftConnection.value.mode === 'proxy')
      draftConnection.value.endpoint = validateProxyEndpoint(draftConnection.value.endpoint)
    connection.value = { ...draftConnection.value }
    settingsOpen.value = false
    centers.value = []
    selectedId.value = null
    rawResponse.value = null
    lastRun.value = null
    error.value = ''
    errorCode.value = ''
    steps.value = createSteps()
    notify('연결 설정을 적용했습니다. 조회 실행으로 데이터를 불러오세요.')
  } catch (e) {
    settingsError.value = e instanceof Error ? e.message : '설정을 확인하세요.'
  }
}
async function run() {
  if (running.value) return
  const snapshot = {
    query: query.value.trim(),
    region: region.value,
    connection: { ...connection.value },
    scenario: scenario.value,
  }
  running.value = true
  centers.value = []
  selectedId.value = null
  rawResponse.value = null
  error.value = ''
  errorCode.value = ''
  steps.value = createSteps()
  const started = performance.now()
  let currentStep = 0
  let count = 0
  try {
    steps.value[0]!.status = 'running'
    await wait(180)
    if (snapshot.query.length > 100)
      throw new CenterApiError('검색어는 100자 이내로 입력하세요.', 'INPUT_ERROR')
    steps.value[0]!.detail = `지역: ${snapshot.region} / 검색: ${snapshot.query || '전체'}`
    steps.value[0]!.status = 'success'
    currentStep = 1
    steps.value[1]!.status = 'running'
    steps.value[1]!.detail =
      snapshot.connection.mode === 'mock'
        ? '명세 기반 목업 응답 대기 중'
        : `GET ${snapshot.connection.endpoint}`
    const response = await requestCenters(snapshot.connection, snapshot.scenario)
    rawResponse.value = response
    steps.value[1]!.detail = `GET /centerList · ${snapshot.connection.mode === 'mock' ? '목업' : '프록시'} 응답 수신`
    steps.value[1]!.status = 'success'
    currentStep = 2
    steps.value[2]!.status = 'running'
    await wait(200)
    const valid = validateResponse(response)
    steps.value[2]!.detail = `resultCode: ${valid.resultCode} · 필수 필드 및 좌표 검증 완료`
    steps.value[2]!.status = 'success'
    currentStep = 3
    steps.value[3]!.status = 'running'
    await wait(180)
    const result = filterCenters(valid.resultData, snapshot.query, snapshot.region)
    count = result.length
    steps.value[3]!.detail = `전체 ${valid.resultCount}개 → 조건에 맞는 ${count}개`
    steps.value[3]!.status = 'success'
    currentStep = 4
    steps.value[4]!.status = 'running'
    await wait(120)
    centers.value = result
    selectedId.value = result[0]?.centerId ?? null
    steps.value[4]!.detail = count
      ? `${count}개 센터를 화면에 표시했습니다.`
      : '조건에 맞는 센터가 없습니다.'
    steps.value[4]!.status = 'success'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '알 수 없는 오류가 발생했습니다.'
    errorCode.value = e instanceof CenterApiError ? e.code : 'UNKNOWN_ERROR'
    steps.value[currentStep]!.status = 'error'
    steps.value[currentStep]!.detail = error.value
  } finally {
    const record: RunRecord = {
      id: Date.now(),
      time: new Date().toLocaleTimeString('ko-KR', { hour12: false }),
      query: snapshot.query,
      region: snapshot.region,
      mode: snapshot.connection.mode,
      scenario: snapshot.scenario,
      status: error.value ? 'error' : 'success',
      duration: Math.round(performance.now() - started),
      count,
      message: error.value || `${count}개 센터 조회 완료`,
    }
    lastRun.value = record
    records.value = [record, ...records.value].slice(0, 30)
    running.value = false
  }
}
function resetFilters() {
  query.value = ''
  region.value = '전체'
  void run()
}
function downloadResults() {
  const url = URL.createObjectURL(
    new Blob(
      [
        JSON.stringify(
          {
            source: lastRun.value?.mode,
            filters: { query: lastRun.value?.query, region: lastRun.value?.region },
            centers: centers.value,
          },
          null,
          2,
        ),
      ],
      { type: 'application/json' },
    ),
  )
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'tms-centers.json'
  anchor.click()
  URL.revokeObjectURL(url)
  notify('조회 결과를 JSON 파일로 저장했습니다.')
}
onMounted(run)
</script>

<template>
  <div class="workspace-page">
    <WorkspaceHeader>
      <a :href="API_REFERENCE" target="_blank" rel="noreferrer"
        >API 명세서<ArrowUpRight :size="15"
      /></a>
      <button class="header-cta" :disabled="running" @click="openSettings">연결 설정</button>
    </WorkspaceHeader>

    <main class="workspace-main">
      <section class="workspace-hero">
        <div class="page-container">
          <h1>
            {{
              activePage === 'centers'
                ? '센터 조회하기'
                : activePage === 'flow'
                  ? '조회 처리 과정'
                  : '실행 기록'
            }}
          </h1>
          <PageSteps
            v-if="activePage !== 'history'"
            :items="pageSections"
            :active="activeSection"
            @select="navigateSection"
          />
          <p v-else class="hero-description">현재 탭에서 실행한 조회 결과와 오류 기록입니다.</p>
        </div>
      </section>

      <div class="workspace-body">
        <div class="page-container">
          <div v-if="activePage !== 'history'" class="workspace-columns">
            <div class="primary-column">
              <section id="lookup" tabindex="-1" class="panel search-panel">
                <div class="section-title">
                  <h2>센터 조회 정보</h2>
                  <span class="mode-label">{{
                    connection.mode === 'mock' ? '목업 데이터 모드' : '프록시 연결 모드'
                  }}</span>
                </div>
                <form id="center-query" class="search-form" @submit.prevent="run">
                  <label class="search-field"
                    ><span class="field-label">센터 검색</span
                    ><span class="input-wrap"
                      ><input
                        v-model="query"
                        type="search"
                        placeholder="센터명, 주소 또는 센터 ID를 입력해 주세요."
                        aria-label="센터 검색"
                        maxlength="100"
                        :disabled="running" /><Search :size="20" /></span
                  ></label>
                  <label class="region-field"
                    ><span class="field-label">지역 선택<span class="required-mark">*</span></span
                    ><select v-model="region" aria-label="지역" :disabled="running">
                      <option value="전체">전체 지역</option>
                      <option v-for="area in regions" :key="area" :value="area">{{ area }}</option>
                    </select></label
                  >
                  <label class="scenario-field"
                    ><span class="field-label"
                      >{{ connection.mode === 'mock' ? '테스트 시나리오' : '응답 모드'
                      }}<span class="required-mark">*</span></span
                    ><select
                      v-if="connection.mode === 'mock'"
                      v-model="scenario"
                      aria-label="테스트 시나리오"
                      :disabled="running"
                    >
                      <option v-for="item in scenarios" :key="item.value" :value="item.value">
                        {{ item.label }}
                      </option></select
                    ><input v-else value="실제 API 응답" aria-label="응답 모드" disabled
                  /></label>
                </form>
                <div class="search-foot">
                  <span>검색 조건은 조회된 센터 목록에 적용됩니다.</span
                  ><button class="text-button" :disabled="running" @click="resetFilters">
                    <RotateCcw :size="14" />조건 초기화
                  </button>
                </div>
              </section>
              <div v-if="error" class="error-banner" role="alert">
                <span
                  ><strong>{{ errorCode }}</strong
                  >{{ error }}</span
                ><button class="button secondary" :disabled="running" @click="run">
                  다시 실행
                </button>
              </div>
              <section
                v-if="activePage === 'centers'"
                id="results"
                tabindex="-1"
                class="panel centers-panel"
              >
                <div class="section-title">
                  <h2>센터 목록</h2>
                  <span class="count-chip">{{ centers.length }}</span
                  ><span class="subtle source-caption">{{
                    lastRun?.mode === 'proxy' ? 'API 응답' : '샘플 데이터'
                  }}</span
                  ><button
                    class="text-button push-right"
                    :disabled="running || !lastRun || !!error"
                    @click="downloadResults"
                  >
                    <ArrowDownToLine :size="14" />JSON 내보내기
                  </button>
                </div>
                <CenterMap
                  :centers="centers"
                  :selected-id="selectedId"
                  @select="selectedId = $event"
                />
                <div class="list-caption">
                  <span>{{ appliedFilter }}</span
                  ><span>목록에서 센터를 선택하면 상세 정보를 표시합니다.</span>
                </div>
                <div v-if="running" class="empty-state" role="status">
                  <LoaderCircle :size="25" class="spin" /><strong>센터를 불러오고 있습니다</strong
                  ><span>실행 결과에서 처리 과정을 확인하세요.</span>
                </div>
                <div v-else-if="!centers.length" class="empty-state">
                  <Search :size="26" /><strong>{{
                    error
                      ? '센터 목록을 불러오지 못했습니다'
                      : lastRun
                        ? '조회된 센터가 없습니다'
                        : '센터 조회를 실행해 주세요'
                  }}</strong
                  ><span>{{
                    error
                      ? '오류 내용을 확인한 뒤 다시 실행해 주세요.'
                      : '검색 조건 또는 테스트 시나리오를 변경하세요.'
                  }}</span>
                </div>
                <div v-else class="table-scroll">
                  <table class="center-table">
                    <thead>
                      <tr>
                        <th>센터명 / ID</th>
                        <th>주소</th>
                        <th>최근 업데이트</th>
                        <th><span class="sr-only">상세 보기</span></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="center in centers"
                        :key="center.centerId"
                        :class="{ selected: selectedId === center.centerId }"
                        @click="selectedId = center.centerId"
                      >
                        <td>
                          <button
                            class="center-name"
                            :aria-label="`${center.centerName} 상세 보기`"
                            :aria-pressed="selectedId === center.centerId"
                            @click.stop="selectedId = center.centerId"
                          >
                            <span class="center-icon"><Box :size="17" /></span
                            ><span
                              ><strong>{{ center.centerName }}</strong
                              ><small>{{ center.centerId }}</small></span
                            >
                          </button>
                        </td>
                        <td class="address-cell">{{ center.address }}</td>
                        <td class="date-cell">{{ center.updateDate.slice(0, 10) }}</td>
                        <td><ChevronRight :size="14" /></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="table-footer">
                  <span>총 {{ centers.length }}개 센터</span
                  ><span
                    >GET /centerList<span class="footer-dot">·</span>
                    {{ lastRun?.time ?? '실행 대기' }}</span
                  >
                </div>
              </section>

              <section
                v-if="activePage === 'flow'"
                id="request"
                tabindex="-1"
                class="panel inspector-panel"
              >
                <div class="section-title">
                  <FileJson :size="17" />
                  <h2>요청과 응답</h2>
                </div>
                <div class="inspector-section">
                  <div class="code-label">
                    REQUEST <span>검색 조건은 API 파라미터로 전송하지 않습니다</span>
                  </div>
                  <pre>{{ JSON.stringify(requestPreview, null, 2) }}</pre>
                </div>
                <div id="response" tabindex="-1" class="inspector-tabs">
                  <button
                    :class="{ active: responseTab === 'summary' }"
                    @click="responseTab = 'summary'"
                  >
                    처리 결과</button
                  ><button
                    :class="{ active: responseTab === 'json' }"
                    @click="responseTab = 'json'"
                  >
                    원본 응답 JSON
                  </button>
                </div>
                <div class="inspector-section">
                  <template v-if="responseTab === 'summary'"
                    ><div class="result-summary">
                      <span class="result-symbol"><Database :size="22" /></span>
                      <h3>
                        {{
                          running
                            ? '응답을 기다리고 있습니다'
                            : error
                              ? '요청 처리 중 오류가 발생했습니다'
                              : lastRun
                                ? `${centers.length}개 센터를 찾았습니다`
                                : '실행 대기 중'
                        }}
                      </h3>
                      <p>
                        {{
                          error ||
                          '명세에 맞는 응답인지 검증한 뒤 검색 조건에 맞는 센터만 표시합니다.'
                        }}
                      </p>
                    </div>
                    <div class="logic-note">
                      <strong>이 데모에서 확인할 수 있는 것</strong>
                      <p>
                        필수 입력 확인 → 센터 목록 조회 → 상태 코드·필드·좌표 검증 → 이름·주소·ID
                        검색 → 결과 표시
                      </p>
                      <span>자연어 해석, LLM 호출, 배차 최적화는 포함되지 않습니다.</span>
                    </div></template
                  >
                  <pre v-else class="response-json">{{
                    rawResponse
                      ? JSON.stringify(rawResponse, null, 2)
                      : '아직 수신한 응답이 없습니다.'
                  }}</pre>
                </div>
              </section>
            </div>
            <aside class="secondary-column">
              <section class="summary-card" aria-labelledby="summary-title">
                <h2 id="summary-title">조회 정보</h2>
                <dl class="summary-list">
                  <div>
                    <dt>서비스 이름</dt>
                    <dd>Badaro</dd>
                  </div>
                  <div>
                    <dt>조회 지역</dt>
                    <dd>{{ region === '전체' ? '전체 지역' : region }}</dd>
                  </div>
                  <div>
                    <dt>검색어</dt>
                    <dd :class="{ placeholder: !query.trim() }">
                      {{ query.trim() || '전체 센터를 조회합니다' }}
                    </dd>
                  </div>
                  <div>
                    <dt>데이터 소스</dt>
                    <dd>{{ connection.mode === 'mock' ? '샘플 데이터' : '실제 API' }}</dd>
                  </div>
                </dl>
                <div class="summary-total">
                  <h3>조회된 센터</h3>
                  <strong>{{ running ? '—' : centers.length }}<span>개</span></strong>
                </div>
                <div class="summary-notice">
                  <Radio :size="20" />
                  <p>
                    {{
                      connection.mode === 'mock'
                        ? 'API 키 없이 목업 데이터를 조회합니다.'
                        : '연결한 서버의 응답을 확인합니다.'
                    }}
                  </p>
                </div>
                <button
                  class="button primary run-button"
                  form="center-query"
                  type="submit"
                  :disabled="running"
                >
                  <LoaderCircle v-if="running" :size="20" class="spin" />{{
                    running ? '조회 중' : '조회 실행'
                  }}<ArrowRight v-if="!running" :size="20" />
                </button>
                <div class="summary-status" role="status">
                  <span :class="['status-dot', { failed: error, busy: running }]"></span
                  ><span>{{
                    running ? '실행 중' : error ? '실행 실패' : lastRun ? '정상 완료' : '대기 중'
                  }}</span
                  ><span class="push-right">{{ completedSteps }} / 5 단계</span>
                </div>
                <div v-if="lastRun && !running" class="summary-metrics">
                  <span>{{ filteredRegions }}개 지역</span
                  ><span
                    >{{ (lastRun.duration / 1000).toFixed(2) }}초 ·
                    {{ lastRun.mode === 'mock' ? '목업 실행' : 'API 실행' }}</span
                  >
                </div>
              </section>
              <section
                v-if="activePage === 'centers'"
                id="center-detail"
                tabindex="-1"
                class="panel detail-panel"
              >
                <div class="section-title">
                  <h2>선택한 센터</h2>
                  <MapPin :size="16" class="push-right muted" />
                </div>
                <template v-if="selected"
                  ><div class="detail-name">
                    <span class="detail-icon"><Box :size="23" /></span>
                    <div>
                      <h3>{{ selected.centerName }}</h3>
                      <code>{{ selected.centerId }}</code>
                    </div>
                  </div>
                  <dl class="detail-list">
                    <div>
                      <dt>주소</dt>
                      <dd>{{ selected.address }}</dd>
                    </div>
                    <div>
                      <dt>위도 / 경도</dt>
                      <dd class="coordinates">
                        {{ selected.latitude.toFixed(6) }}<br />{{ selected.longitude.toFixed(6) }}
                      </dd>
                    </div>
                    <div>
                      <dt>고유 번호</dt>
                      <dd>{{ selected.seq }}</dd>
                    </div>
                    <div>
                      <dt>업데이트</dt>
                      <dd>{{ selected.updateDate }}</dd>
                    </div>
                  </dl></template
                >
                <div v-else class="empty-state">
                  <MapPin :size="28" />
                  <p>목록에서 센터를 선택해 주세요.</p>
                </div>
              </section>
              <section id="execution" tabindex="-1" class="panel flow-panel">
                <div class="section-title">
                  <span class="heading-icon"><GitBranch :size="17" /></span>
                  <h2>동작 흐름</h2>
                  <span :class="['flow-badge', { failed: error }]">{{
                    running ? '실행 중' : error ? '실패' : lastRun ? '완료' : '대기'
                  }}</span>
                </div>
                <p class="panel-description">입력 확인, API 호출, 응답 검증, 검색, 결과 표시 순서입니다.</p>
                <ol class="flow-steps" aria-live="polite">
                  <li v-for="(step, index) in steps" :key="step.title" :class="step.status">
                    <span class="step-marker"
                      ><Check v-if="step.status === 'success'" :size="13" /><LoaderCircle
                        v-else-if="step.status === 'running'"
                        :size="13"
                        class="spin"
                      /><X v-else-if="step.status === 'error'" :size="13" /><span v-else>{{
                        index + 1
                      }}</span></span
                    >
                    <div>
                      <strong>{{ step.title }}</strong
                      ><span class="step-description">{{ step.description }}</span>
                      <p v-if="step.detail" class="step-detail">{{ step.detail }}</p>
                    </div>
                    <span class="step-status">{{
                      step.status === 'success'
                        ? '완료'
                        : step.status === 'running'
                          ? '진행'
                          : step.status === 'error'
                            ? '오류'
                            : '대기'
                    }}</span>
                  </li>
                </ol>
                <div class="flow-foot">
                  <Terminal :size="13" /><span>규칙 기반 데모 · LLM 미연결</span
                  ><span class="push-right">{{ completedSteps }}/5</span>
                </div>
              </section>
            </aside>
          </div>
          <section v-if="activePage === 'history'" class="panel history-panel">
            <div class="section-title">
              <History :size="18" />
              <h2>센터 조회 기록</h2>
              <span class="count-chip">{{ records.length }}</span
              ><span class="subtle push-right">새로고침하면 초기화됩니다</span>
            </div>
            <div class="history-filters" aria-label="실행 기록 필터">
              <button
                v-for="filter in [
                  { id: 'all', label: '전체 기록' },
                  { id: 'success', label: '완료' },
                  { id: 'error', label: '실패' },
                ]"
                :key="filter.id"
                :class="{ active: historyFilter === filter.id }"
                :aria-pressed="historyFilter === filter.id"
                @click="historyFilter = filter.id"
              >
                {{ filter.label }}
              </button>
            </div>
            <div class="table-scroll">
              <table class="history-table">
                <thead>
                  <tr>
                    <th>실행 시각</th>
                    <th>검색 조건</th>
                    <th>데이터 모드</th>
                    <th>결과</th>
                    <th>소요 시간</th>
                    <th>상태</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in visibleRecords" :key="record.id">
                    <td class="mono">{{ record.time }}</td>
                    <td>
                      <strong>{{ record.query || '전체 센터' }}</strong
                      ><small
                        >{{ record.region }} ·
                        {{
                          record.mode === 'mock'
                            ? scenarios.find((s) => s.value === record.scenario)?.label
                            : '실제 API'
                        }}</small
                      >
                    </td>
                    <td>{{ record.mode === 'mock' ? '목업' : '프록시' }}</td>
                    <td>{{ record.message }}</td>
                    <td class="mono">{{ (record.duration / 1000).toFixed(2) }}s</td>
                    <td>
                      <span :class="['history-status', { failed: record.status === 'error' }]">{{
                        record.status === 'success' ? '완료' : '실패'
                      }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="!visibleRecords.length" class="empty-state">
              조건에 맞는 실행 기록이 없습니다.
            </div>
          </section>

          <TmsHistory v-if="activePage === 'history'" />
          <footer class="page-footer">
            <RouterLink to="/" class="footer-brand">Badaro</RouterLink
            ><span>센터·차량·배송지·배차 관리</span
            ><a :href="API_REFERENCE" target="_blank" rel="noreferrer"
              >SK open API 명세 기반<ExternalLink :size="14"
            /></a>
          </footer>
        </div>
      </div>
    </main>
    <Teleport to="body">
      <dialog
        ref="settingsDialog"
        class="modal-backdrop"
        aria-labelledby="settings-title"
        @close="settingsOpen = false"
        @click.self="settingsOpen = false"
      >
        <section class="settings-modal">
          <div class="modal-heading">
            <span class="heading-icon"><Settings2 :size="20" /></span>
            <h2 id="settings-title">API 연결 설정</h2>
            <button
              class="icon-button push-right"
              aria-label="설정 닫기"
              @click="settingsOpen = false"
            >
              <X :size="20" />
            </button>
          </div>
          <p class="modal-intro">목업 데이터를 사용하거나 센터 목록 조회 서버를 연결할 수 있습니다.</p>
          <form @submit.prevent="saveSettings">
            <fieldset class="mode-options">
              <legend>데이터 소스</legend>
              <label :class="{ chosen: draftConnection.mode === 'mock' }"
                ><input v-model="draftConnection.mode" type="radio" value="mock" /><span
                  ><strong>목업 데이터</strong
                  ><small>앱 키 없이 센터 조회 테스트를 실행합니다.</small></span
                ><span class="recommended">기본</span></label
              ><label :class="{ chosen: draftConnection.mode === 'proxy' }"
                ><input v-model="draftConnection.mode" type="radio" value="proxy" /><span
                  ><strong>실제 API · 서버 프록시</strong
                  ><small>같은 출처의 서버를 통해 센터 목록을 조회합니다.</small></span
                ></label
              >
            </fieldset>
            <label v-if="draftConnection.mode === 'proxy'" class="proxy-field"
              ><span class="field-label">프록시 경로</span
              ><input
                v-model="draftConnection.endpoint"
                placeholder="/api/tms/centerList"
                required
              /><small
                >프록시 서버는 별도 연결이 필요합니다. 앱 키는 서버에서 설정하세요.</small
              ></label
            >
            <div class="settings-note">
              <strong>연결할 API</strong><code>GET {{ API_URL }}</code>
              <p>
                이 화면은 프론트엔드 데모입니다. 실제 호출용 서버는 아직 포함되어 있지 않으며, 연결
                실패 시 오류를 그대로 표시합니다.
              </p>
              <a :href="API_REFERENCE" target="_blank" rel="noreferrer"
                >API 명세서 보기<ArrowUpRight :size="13"
              /></a>
            </div>
            <p v-if="settingsError" class="error-text" role="alert">{{ settingsError }}</p>
            <div class="modal-actions">
              <button class="button secondary" type="button" @click="settingsOpen = false">
                취소</button
              ><button class="button primary" type="submit">설정 적용<Check :size="15" /></button>
            </div>
          </form>
        </section>
      </dialog>
      <div v-if="toast" class="toast" role="status"><Check :size="16" />{{ toast }}</div>
    </Teleport>
  </div>
</template>
