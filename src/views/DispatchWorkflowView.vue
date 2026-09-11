<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import WorkspaceHeader from '../components/WorkspaceHeader.vue'
import TmsResources from '../components/TmsResources.vue'
import DispatchRouteDetails from '../components/DispatchRouteDetails.vue'
import { dispatchSteps, dispatchWorkflow as flow } from '../stores/dispatch-workflow'
import { tmsState } from '../stores/tms'
import { vehicleTypes } from '../services/tms-mock'
import '../logistics.css'
import '../dispatch-workflow.css'
const { state, center, orders, vehicles, availableVehicles, weight, totalAssigned } = flow
const search = ref('')
const heading = ref<HTMLElement | null>(null)
const manageOrders = ref(false)
const matches = (row: Record<string, string | number>) =>
  JSON.stringify(row).toLocaleLowerCase().includes(search.value.toLocaleLowerCase())
const shownCenters = computed(() => tmsState.centers.filter(matches))
const shownOrders = computed(() => tmsState.orders.filter(matches))
const shownVehicles = computed(() => tmsState.vehicles.filter(matches))
const instructions = [
  '오늘 배송을 시작할 출발 센터를 선택해 주세요.',
  '주문을 등록하고 오늘 배송할 주문만 선택해 주세요.',
  '선택한 주문을 배송할 차량을 골라 주세요. 운행 제외 차량은 선택할 수 없습니다.',
  '출발 시간과 배송을 나눌 기준을 설정해 주세요.',
  '출발 센터, 주문, 차량, 조건을 확인한 뒤 배차를 요청하세요.',
  '선택한 주문과 차량을 바탕으로 배송 계획을 계산하고 있습니다.',
  '배차된 주문과 미배차 사유를 확인해 주세요.',
  '차량별로 방문 순서와 예상 도착 시간, 경로를 확인해 주세요.',
]
const nextLabel = computed(
  () =>
    ({
      1: '주문 등록/선택',
      2: '차량 선택',
      3: '배차 조건 설정',
      4: '배차 요청 확인',
      7: '차량별 배송 상세 확인',
    })[state.step as 1 | 2 | 3 | 4 | 7],
)
watch(
  () => state.step,
  async () => {
    search.value = ''
    manageOrders.value = false
    await nextTick()
    heading.value?.focus({ preventScroll: true })
    heading.value?.scrollIntoView({ block: 'start', behavior: 'instant' })
  },
)
function toggleAll(kind: 'orders' | 'vehicles') {
  if (kind === 'orders')
    state.orderIds =
      state.orderIds.length === tmsState.orders.length
        ? []
        : tmsState.orders.map((o) => String(o.orderId))
  else
    state.vehicleIds =
      state.vehicleIds.length === availableVehicles.value.length
        ? []
        : availableVehicles.value.map((v) => String(v.vehicleId))
}
</script>
<template>
  <div class="workspace-page logistics-page workflow-page">
    <WorkspaceHeader />
    <main>
      <section class="workspace-hero">
        <div class="page-container">
          <p class="workflow-eyebrow">TODAY’S DELIVERY</p>
          <h1>오늘의 배송 준비</h1>
          <p class="logistics-intro">출발 센터, 주문, 차량을 선택하고 배차 조건을 설정하세요.</p>
          <nav aria-label="배차 진행 단계" class="workflow-steps">
            <ol>
              <li
                v-for="(label, i) in dispatchSteps"
                :key="label"
                :class="{ active: state.step === i + 1, completed: i + 1 < state.step }"
              >
                <button
                  :disabled="!flow.canVisit(i + 1)"
                  :aria-current="state.step === i + 1 ? 'step' : undefined"
                  @click="flow.go(i + 1)"
                >
                  <span>{{ String(i + 1).padStart(2, '0') }}</span
                  >{{ label }}
                </button>
              </li>
            </ol>
          </nav>
        </div>
      </section>
      <div class="logistics-body">
        <div class="page-container logistics-grid">
          <div class="logistics-content">
            <section class="tms-card workflow-card" :aria-busy="state.busy">
              <div class="tms-section-heading">
                <div>
                  <p class="step-kicker">STEP {{ String(state.step).padStart(2, '0') }} / 08</p>
                  <h2 ref="heading" tabindex="-1">
                    {{ state.step }}. {{ dispatchSteps[state.step - 1] }}
                  </h2>
                  <p>{{ instructions[state.step - 1] }}</p>
                </div>
              </div>
              <p v-if="state.notice" role="status" class="tms-notice">{{ state.notice }}</p>
              <div v-if="state.step <= 3" class="workflow-search">
                <input
                  v-model="search"
                  type="search"
                  :aria-label="
                    state.step === 1 ? '센터 검색' : state.step === 2 ? '주문 검색' : '차량 검색'
                  "
                  placeholder="이름, ID, 주소로 검색"
                /><button
                  v-if="state.step !== 1"
                  class="tms-secondary"
                  @click="toggleAll(state.step === 2 ? 'orders' : 'vehicles')"
                >
                  {{
                    state.step === 2
                      ? state.orderIds.length === tmsState.orders.length
                        ? '주문 선택 해제'
                        : '주문 전체 선택'
                      : state.vehicleIds.length === availableVehicles.length
                        ? '차량 선택 해제'
                        : '가능 차량 전체 선택'
                  }}
                </button>
              </div>
              <template v-if="state.step === 1">
                <fieldset class="choice-list">
                  <legend class="sr-only">출발 센터 선택</legend>
                  <label
                    v-for="c in shownCenters"
                    :key="c.centerId"
                    :class="['workflow-choice', { selected: state.centerId === c.centerId }]"
                    ><input
                      v-model="state.centerId"
                      type="radio"
                      name="departure-center"
                      :value="String(c.centerId)"
                      :aria-label="`${c.centerName} 선택`"
                    />
                    <div>
                      <strong>{{ c.centerName }}</strong>
                      <p>{{ c.address }}</p>
                      <small>{{ c.centerId }}</small>
                    </div>
                    <span class="choice-check" aria-hidden="true">{{
                      state.centerId === c.centerId ? '✓' : ''
                    }}</span></label
                  >
                </fieldset>
                <p v-if="!shownCenters.length" class="tms-empty">
                  선택할 센터가 없습니다. 검색 조건을 확인하거나 센터를 등록해 주세요.
                </p>
                <RouterLink to="/workspace/centers" class="workflow-text-link"
                  >센터 정보 관리 ↗</RouterLink
                >
              </template>
              <template v-else-if="state.step === 2">
                <div class="selection-info">
                  <span
                    >선택 주문 <strong>{{ orders.length }}건</strong></span
                  ><span>총 중량 {{ weight.toLocaleString() }} kg</span
                  ><button
                    class="workflow-text-link"
                    :aria-expanded="manageOrders"
                    @click="manageOrders = !manageOrders"
                  >
                    {{ manageOrders ? '주문 관리 닫기' : '주문 등록·관리' }}
                  </button>
                </div>
                <div v-if="manageOrders" class="inline-order-manager">
                  <TmsResources initial="orders" fixed-resource />
                </div>
                <fieldset class="choice-list">
                  <legend class="sr-only">오늘 배송할 주문 선택</legend>
                  <label
                    v-for="o in shownOrders"
                    :key="o.orderId"
                    :class="[
                      'workflow-choice',
                      { selected: state.orderIds.includes(String(o.orderId)) },
                    ]"
                    ><input
                      v-model="state.orderIds"
                      type="checkbox"
                      :value="String(o.orderId)"
                      :aria-label="`${o.orderName} 선택`"
                    />
                    <div>
                      <strong>{{ o.orderName }}</strong>
                      <p>{{ o.address }}</p>
                      <small
                        >{{ o.deliveryWeight }} kg · {{ o.deliveryVolume }} cbm · 작업
                        {{ o.serviceTime }}분 ·
                        {{ vehicleTypes[o.vehicleType as keyof typeof vehicleTypes] }}</small
                      >
                    </div>
                    <span class="choice-check" aria-hidden="true">{{
                      state.orderIds.includes(String(o.orderId)) ? '✓' : ''
                    }}</span></label
                  >
                </fieldset>
                <p v-if="!shownOrders.length" class="tms-empty">
                  배송할 주문이 없습니다. 새 주문을 등록하거나 검색 조건을 확인해 주세요.
                </p>
              </template>
              <template v-else-if="state.step === 3">
                <div class="selection-info">
                  <span
                    >선택 차량 <strong>{{ vehicles.length }}대</strong></span
                  ><span>운행 가능 {{ availableVehicles.length }}대</span>
                </div>
                <fieldset class="choice-list">
                  <legend class="sr-only">운행 가능한 차량 선택</legend>
                  <label
                    v-for="v in shownVehicles"
                    :key="v.vehicleId"
                    :class="[
                      'workflow-choice',
                      {
                        selected: state.vehicleIds.includes(String(v.vehicleId)),
                        unavailable: v.inputYn === '0',
                      },
                    ]"
                    ><input
                      v-model="state.vehicleIds"
                      type="checkbox"
                      :value="String(v.vehicleId)"
                      :disabled="v.inputYn === '0'"
                      :aria-label="`${v.vehicleName} 선택`"
                    />
                    <div>
                      <strong>{{ v.vehicleName }}</strong>
                      <p>
                        {{ vehicleTypes[v.vehicleType as keyof typeof vehicleTypes] }} · 최대
                        {{ v.weight }} ton / {{ v.volume }} cbm
                      </p>
                      <small
                        >권역 {{ v.zoneCode || '미지정' }} · 숙련도 {{ v.skillPer }}% ·
                        {{ v.inputYn === '0' ? '운행 제외' : '운행 가능' }}</small
                      >
                    </div>
                    <span class="choice-check" aria-hidden="true">{{
                      state.vehicleIds.includes(String(v.vehicleId)) ? '✓' : ''
                    }}</span></label
                  >
                </fieldset>
                <p v-if="!shownVehicles.length" class="tms-empty">
                  선택할 차량이 없습니다. 차량 정보와 검색 조건을 확인해 주세요.
                </p>
                <RouterLink to="/workspace/vehicles" class="workflow-text-link"
                  >차량 정보 관리 ↗</RouterLink
                >
              </template>
              <form
                v-else-if="state.step === 4"
                id="dispatch-options"
                class="tms-fields"
                @submit.prevent="flow.next()"
              >
                <label>출발 시간<input v-model="state.startTime" type="time" required /></label>
                <label
                  >배차 기준<select v-model="state.optionType" aria-label="배차 기준">
                    <option value="1">중량 기준</option>
                    <option value="2">부피 기준</option>
                    <option value="3">주문 수 기준</option>
                  </select></label
                >
                <label
                  >균등화 기준<select v-model="state.equalizationType">
                    <option value="1">적용 안 함</option>
                    <option value="2">거리 균등화</option>
                    <option value="3">시간 균등화</option>
                  </select></label
                >
                <label
                  >센터 복귀<select v-model="state.centerReturnYn">
                    <option value="Y">선택한 센터로 복귀</option>
                    <option value="N">복귀 안 함</option>
                  </select></label
                >
                <label
                  >경로 데이터<select v-model="state.routeYn" aria-label="경로 데이터">
                    <option value="Y">경로 포함</option>
                    <option value="N">배송 순서만 확인</option>
                  </select></label
                >
              </form>
              <template v-else-if="state.step === 5">
                <dl class="workflow-review">
                  <div>
                    <dt>출발 센터</dt>
                    <dd>
                      {{ center?.centerName }}<small>{{ center?.address }}</small>
                    </dd>
                  </div>
                  <div>
                    <dt>오늘 배송할 주문</dt>
                    <dd>
                      {{ orders.length }}건 · {{ weight.toLocaleString() }} kg<small>{{
                        orders.map((o) => o.orderName).join(', ')
                      }}</small>
                    </dd>
                  </div>
                  <div>
                    <dt>투입 차량</dt>
                    <dd>
                      {{ vehicles.length }}대<small>{{
                        vehicles.map((v) => v.vehicleName).join(', ')
                      }}</small>
                    </dd>
                  </div>
                  <div>
                    <dt>출발 시간</dt>
                    <dd>{{ state.startTime }}</dd>
                  </div>
                  <div>
                    <dt>배차 기준</dt>
                    <dd>{{ { '1': '중량', '2': '부피', '3': '주문 수' }[state.optionType] }}</dd>
                  </div>
                  <div>
                    <dt>균등화</dt>
                    <dd>
                      {{
                        { '1': '적용 안 함', '2': '거리 균등화', '3': '시간 균등화' }[
                          state.equalizationType
                        ]
                      }}
                    </dd>
                  </div>
                  <div>
                    <dt>센터 복귀 / 경로</dt>
                    <dd>
                      {{ state.centerReturnYn === 'Y' ? '복귀' : '복귀 안 함' }} /
                      {{ state.routeYn === 'Y' ? '경로 포함' : '경로 제외' }}
                    </dd>
                  </div>
                </dl>
                <p class="tms-notice">
                  선택한 주문과 차량만 배차에 사용합니다. 목업 데이터로 계산하며 실제 배차가
                  전송되지는 않습니다.
                </p>
              </template>
              <div v-else-if="state.step === 6" class="workflow-calculating" role="status">
                <div class="calculation-ripple" aria-hidden="true">
                  <span></span><span></span><span></span>
                </div>
                <h3>배송 계획을 계산하고 있습니다</h3>
                <p>
                  {{
                    state.mappingKey
                      ? '배차 요청이 접수되었습니다. 결과를 확인하고 있습니다.'
                      : '선택한 주문과 차량으로 배차를 요청하고 있습니다.'
                  }}
                </p>
                <p>
                  {{ state.snapshot?.centerName }} · 주문 {{ orders.length }}건 · 차량
                  {{ vehicles.length }}대
                </p>
                <small>결과가 준비되면 다음 단계로 이동합니다.</small>
              </div>
              <template v-else-if="state.step === 7 && state.result">
                <div class="dispatch-totals">
                  <div>
                    <strong>{{ state.result.vehicleCount }}</strong
                    ><span>배차 차량</span>
                  </div>
                  <div>
                    <strong>{{ totalAssigned }}</strong
                    ><span>배차 주문</span>
                  </div>
                  <div>
                    <strong>{{ state.result.mock.unassigned.length }}</strong
                    ><span>미배차 주문</span>
                  </div>
                </div>
                <div class="workflow-plan-list">
                  <div v-for="v in state.result.vehicleList" :key="v.vehicleId">
                    <strong>{{ v.vehicleName }}</strong
                    ><span>{{ v.deliveryCount }}건 · {{ v.deliveryWeight }} kg</span
                    ><small
                      >약 {{ Math.ceil(v.deliveryTime / 60) }}분 ·
                      {{ (v.deliveryDistance / 1000).toFixed(1) }} km</small
                    >
                  </div>
                </div>
                <div v-if="state.result.mock.unassigned.length" class="unassigned">
                  <h3>미배차 주문</h3>
                  <p v-for="o in state.result.mock.unassigned" :key="o.orderId">
                    <strong>{{ o.orderName }}</strong
                    ><span>{{ o.reason }}</span>
                  </p>
                </div>
                <p v-else class="tms-notice">선택한 주문이 모두 배차되었습니다.</p>
                <p v-if="!state.result.vehicleList.length" class="tms-notice">
                  배차 가능한 차량이 없습니다. 주문·차량·조건을 수정한 뒤 다시 요청해 주세요.
                </p>
                <details class="api-details">
                  <summary>요청·계산 정보</summary>
                  <p>
                    출발 센터: {{ state.snapshot?.centerName }} · {{ state.snapshot?.centerId }}
                  </p>
                  <p class="mapping-key">
                    mappingKey <code>{{ state.mappingKey }}</code>
                  </p>
                  <pre>{{ JSON.stringify(state.snapshot?.request, null, 2) }}</pre>
                  <ul>
                    <li v-for="a in state.result.mock.assumptions" :key="a">{{ a }}</li>
                  </ul>
                  <p>{{ state.result.mock.routing }}</p>
                </details>
              </template>
              <DispatchRouteDetails
                v-else-if="state.step === 8 && state.result"
                :result="state.result"
              />
              <p v-if="state.error" role="alert" class="tms-notice error">{{ state.error }}</p>
              <div v-if="state.step !== 6" class="workflow-actions">
                <button
                  v-if="state.step > 1"
                  class="tms-secondary"
                  @click="flow.go(state.step === 7 ? 5 : state.step - 1)"
                >
                  {{ state.step === 7 ? '요청 내용 다시 확인' : '이전 단계' }}</button
                ><span v-else></span>
                <button
                  v-if="nextLabel"
                  type="button"
                  class="tms-primary"
                  :disabled="!!flow.issue(Math.min(state.step, 4))"
                  @click="flow.next()"
                >
                  {{ nextLabel }} <span aria-hidden="true">→</span>
                </button>
                <button
                  v-else-if="state.step === 5"
                  class="tms-primary"
                  :disabled="state.busy || !!flow.issue(4)"
                  @click="flow.run()"
                >
                  배차 요청하기 <span aria-hidden="true">→</span>
                </button>
                <button v-else-if="state.step === 8" class="tms-primary" @click="flow.restart()">
                  새 배송 준비
                </button>
              </div>
              <p v-if="state.step <= 4 && flow.issue(state.step)" class="workflow-hint">
                {{ flow.issue(state.step) }}
              </p>
            </section>
          </div>
          <aside class="logistics-summary workflow-summary">
            <h2>오늘의 배송</h2>
            <dl>
              <div>
                <dt>출발 센터</dt>
                <dd>{{ center?.centerName ?? '선택 전' }}</dd>
              </div>
              <div>
                <dt>배송 주문</dt>
                <dd>{{ orders.length }}건</dd>
              </div>
              <div>
                <dt>투입 차량</dt>
                <dd>{{ vehicles.length }}대</dd>
              </div>
              <div>
                <dt>출발 시간</dt>
                <dd>{{ state.startTime }}</dd>
              </div>
            </dl>
            <div class="summary-total">
              <span>총 배송 중량</span
              ><strong>{{ weight.toLocaleString() }} <small>kg</small></strong>
            </div>
            <p class="tms-notice">
              {{ state.step }} / 8 단계<br />{{ dispatchSteps[state.step - 1] }}
            </p>
            <p class="tms-footnote">목업 시연 · 새로고침하면 선택 내용과 결과가 초기화됩니다.</p>
            <RouterLink to="/workspace/api" class="summary-api"
              >API 요청·응답 살펴보기 ↗</RouterLink
            >
          </aside>
        </div>
      </div>
    </main>
    <footer class="logistics-footer">
      <RouterLink to="/">Badaro</RouterLink><span>센터·차량·배송지·배차 관리</span>
    </footer>
  </div>
</template>
