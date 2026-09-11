<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import {
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Truck,
  MapPin,
  Package,
  LoaderCircle,
  Check,
  Download,
} from '@lucide/vue'
import BadaroLogo from '../components/BadaroLogo.vue'
import DeliveryMap from '../components/DeliveryMap.vue'
import DispatchProgressModal from '../components/DispatchProgressModal.vue'
import AgentChat from '../components/AgentChat.vue'
import LiveCenterLookup from '../components/LiveCenterLookup.vue'
import { createDispatchConsole } from '../stores/dispatch-console'
import { arrival, duration, number, routeColors } from '../services/dispatch-display'

const consoleState = createDispatchConsole()
const {
  data,
  state,
  center,
  availableOrders,
  availableVehicles,
  orders,
  vehicles,
  branchCount,
  weight,
  plans,
  activePlan,
  issue,
} = consoleState
const detailsOpen = ref(false)
const resultHeading = ref<HTMLElement>()
const controlPanel = ref<HTMLElement>()
function scrollToResults() {
  const panel = controlPanel.value
  const heading = resultHeading.value
  if (!panel || !heading) return
  if (getComputedStyle(panel).overflowY === 'auto') {
    panel.scrollTo({
      top:
        panel.scrollTop +
        heading.getBoundingClientRect().top -
        panel.getBoundingClientRect().top -
        12,
    })
  } else {
    heading.scrollIntoView({ block: 'start' })
  }
}
const orderFilter = ref('전체')
const filteredOrders = computed(() =>
  availableOrders.value.filter(
    (o) => orderFilter.value === '전체' || o.itemType === orderFilter.value,
  ),
)
const allOrdersSelected = computed(
  () =>
    filteredOrders.value.length > 0 &&
    filteredOrders.value.every((o) => state.orderIds.includes(String(o.orderId))),
)
const allVehiclesSelected = computed(
  () =>
    availableVehicles.value.length > 0 &&
    availableVehicles.value.every((v) => state.vehicleIds.includes(String(v.vehicleId))),
)
const totals = computed(() =>
  plans.value.reduce(
    (a, p) => ({
      count: a.count + p.deliveryCount,
      weight: a.weight + p.deliveryWeight,
      distance: a.distance + p.deliveryDistance,
      time: a.time + p.deliveryTime,
    }),
    { count: 0, weight: 0, distance: 0, time: 0 },
  ),
)
function toggleOrders() {
  const ids = filteredOrders.value.map((o) => String(o.orderId))
  state.orderIds = allOrdersSelected.value
    ? state.orderIds.filter((id) => !ids.includes(id))
    : [...new Set([...state.orderIds, ...ids])]
}
function toggleVehicles() {
  state.vehicleIds = allVehiclesSelected.value
    ? []
    : availableVehicles.value.map((v) => String(v.vehicleId))
}
async function selectPlan(id: string) {
  state.activeVehicleId = id
  if (!state.visibleVehicleIds.includes(id)) state.visibleVehicleIds.push(id)
  state.resultsOpen = true
  detailsOpen.value = true
  await nextTick()
  scrollToResults()
}
function exportResult() {
  if (!state.result) return
  const url = URL.createObjectURL(
    new Blob(
      [
        JSON.stringify(
          { deliveryDate: state.deliveryDate, request: state.snapshot, ...state.result },
          null,
          2,
        ),
      ],
      { type: 'application/json' },
    ),
  )
  const a = document.createElement('a')
  a.href = url
  a.download = `badaro-${state.deliveryDate}.json`
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
watch(
  () => state.result,
  async (result) => {
    detailsOpen.value = false
    if (result) {
      await nextTick()
      resultHeading.value?.focus({ preventScroll: true })
      scrollToResults()
    }
  },
)
onBeforeUnmount(consoleState.dispose)
</script>

<template>
  <div class="dispatch-console">
    <header class="console-header">
      <RouterLink to="/" class="console-brand" aria-label="Badaro 메인 페이지"
        ><BadaroLogo priority
      /></RouterLink>
      <span class="header-divider" />
      <h1>배송 배차</h1>
      <div class="header-meta">
        <RouterLink to="/" class="operator-badge" title="진입 화면으로 돌아가기"
          >본사물류운영자 전용</RouterLink
        ><span>{{ state.deliveryDate }} <span class="date-caption">배송 데이터</span></span>
      </div>
    </header>

    <main class="console-grid">
      <aside ref="controlPanel" class="control-panel" aria-label="배송 선택과 배차 결과">
        <AgentChat />
        <section class="setup-area" aria-label="배차 설정">
          <fieldset class="setup-fields" :disabled="state.busy">
            <legend class="sr-only">센터, 차량, 배송정보 선택</legend>
            <div class="selection-grid">
              <section class="selection-panel center-panel" aria-labelledby="center-label">
                <h2 id="center-label"><MapPin :size="15" />센터 <span>1곳</span></h2>
                <div class="center-list">
                  <label
                    v-for="item in data.centers"
                    :key="item.centerId"
                    class="center-option"
                    :class="{ chosen: state.centerId === item.centerId }"
                  >
                    <input
                      v-model="state.centerId"
                      type="radio"
                      name="center"
                      :value="item.centerId"
                    />
                    <span
                      ><strong>{{ item.centerName }}</strong
                      ><small>{{ item.address }}</small></span
                    ><Check :size="15" />
                  </label>
                </div>
                <p class="center-caption">서울 전역 · 배송 출발 센터</p>
                <LiveCenterLookup />
              </section>
              <section class="selection-panel" aria-labelledby="vehicle-label">
                <h2 id="vehicle-label">
                  <Truck :size="16" />차량
                  <span>{{ vehicles.length }} / {{ availableVehicles.length }}대</span>
                </h2>
                <div class="selection-tools">
                  <label
                    ><input
                      type="checkbox"
                      :checked="allVehiclesSelected"
                      :indeterminate="vehicles.length > 0 && !allVehiclesSelected"
                      @change="toggleVehicles"
                    />전체 선택</label
                  ><span>차종 / 최대 적재량</span>
                </div>
                <div class="selection-list vehicle-list">
                  <label
                    v-for="vehicle in availableVehicles"
                    :key="vehicle.vehicleId"
                    class="selection-row"
                    :class="{ chosen: state.vehicleIds.includes(String(vehicle.vehicleId)) }"
                  >
                    <input
                      v-model="state.vehicleIds"
                      type="checkbox"
                      :value="String(vehicle.vehicleId)"
                      :aria-label="String(vehicle.vehicleName)"
                    />
                    <span>{{ vehicle.vehicleName }}</span
                    ><small
                      >{{ vehicle.supportedItemTypes }} ·
                      {{ number(Number(vehicle.maxLoadKg)) }} kg</small
                    >
                  </label>
                </div>
              </section>
              <section class="selection-panel" aria-labelledby="order-label">
                <h2 id="order-label">
                  <Package :size="15" />배송정보
                  <span>{{ branchCount }}곳 · {{ orders.length }}건</span>
                </h2>
                <div class="selection-tools">
                  <label
                    ><input
                      type="checkbox"
                      :checked="allOrdersSelected"
                      :indeterminate="
                        !allOrdersSelected &&
                        filteredOrders.some((o) => state.orderIds.includes(String(o.orderId)))
                      "
                      @change="toggleOrders"
                    />전체 선택</label
                  ><select v-model="orderFilter" aria-label="배송 품목 필터">
                    <option v-for="type in ['전체', '활어', '냉장', '냉동', '일반']" :key="type">
                      {{ type }}
                    </option></select
                  ><span>중량 / 희망시간</span>
                </div>
                <div class="selection-list order-list">
                  <label
                    v-for="order in filteredOrders"
                    :key="order.orderId"
                    class="selection-row"
                    :class="{ chosen: state.orderIds.includes(String(order.orderId)) }"
                    :title="String(order.address)"
                  >
                    <input
                      v-model="state.orderIds"
                      type="checkbox"
                      :value="String(order.orderId)"
                      :aria-label="String(order.orderName)"
                    />
                    <span>{{ order.orderName }}</span
                    ><small>{{ order.deliveryWeight }} kg · {{ order.desiredDeliveryTime }}</small>
                  </label>
                  <p v-if="!filteredOrders.length" class="list-empty">
                    해당 품목의 주문이 없습니다.
                  </p>
                </div>
              </section>
            </div>
            <div class="condition-row">
              <span class="condition-label">배차 조건</span>
              <label
                >출발 시간
                <input v-model="state.startTime" type="time" aria-label="출발 시간" required
              /></label>
              <label
                >배분 기준
                <select v-model="state.optionType" aria-label="배분 기준">
                  <option value="1">적재 중량</option>
                  <option value="2">적재 부피</option>
                  <option value="3">주문 건수</option>
                </select></label
              >
              <label class="return-label"
                ><input v-model="state.centerReturn" type="checkbox" />센터로 복귀</label
              >
              <span class="weight-summary"
                >총 배송 중량 <strong>{{ number(weight) }} kg</strong></span
              >
            </div>
          </fieldset>
          <aside class="dispatch-action">
            <div class="truck-illustration" aria-hidden="true">
              <span class="truck-halo" /><Truck :size="76" :stroke-width="1.2" /><Package
                :size="26"
                class="truck-package"
              /><span class="truck-waves" />
            </div>
            <p>센터·차량·배송정보를 확인하고<br />배차를 시작해 주세요.</p>
            <button
              class="primary-button dispatch-button"
              :disabled="!state.busy && !!issue"
              @click="consoleState.run"
            >
              <LoaderCircle v-if="state.busy" class="spin" :size="17" />{{
                state.busy ? '배차 진행 보기' : '배차 요청'
              }}<ArrowRight v-if="!state.busy" :size="17" />
            </button>
            <span v-if="issue && !state.busy" class="selection-issue">{{ issue }}</span>
          </aside>
        </section>
        <div v-if="state.error && !state.modalOpen" class="inline-error" role="alert">
          {{ state.error }} <button @click="consoleState.run">다시 요청</button>
        </div>
        <p class="sr-only" role="status">{{ state.notice }}</p>

        <section class="results-area" aria-labelledby="results-title">
          <header class="results-bar">
            <button
              class="result-toggle"
              :aria-expanded="state.resultsOpen"
              aria-controls="results-content"
              @click="state.resultsOpen = !state.resultsOpen"
            >
              <ChevronDown v-if="state.resultsOpen" :size="19" /><ChevronUp
                v-else
                :size="19"
              /><span class="sr-only">배차 결과 {{ state.resultsOpen ? '접기' : '펼치기' }}</span>
            </button>
            <h2 id="results-title" ref="resultHeading" tabindex="-1">배차 결과</h2>
            <span v-if="state.result" class="result-state"
              ><Check :size="13" />{{ plans.length }}대 · {{ totals.count }}건 배정</span
            >
            <span v-else class="result-state">{{ state.busy ? '계산 중' : '배차 대기' }}</span>
            <div class="result-actions">
              <button
                :disabled="!plans.length"
                @click="state.visibleVehicleIds = plans.map((p) => p.vehicleId)"
              >
                경로 모두 보기</button
              ><button :disabled="!plans.length" @click="state.visibleVehicleIds = []">
                경로 숨기기</button
              ><button
                :disabled="!state.result"
                aria-label="배차 결과 다운로드"
                @click="exportResult"
              >
                <Download :size="15" />
              </button>
            </div>
          </header>
          <div v-show="state.resultsOpen" id="results-content">
            <div class="table-scroll summary-scroll">
              <table class="result-table summary-table">
                <caption class="sr-only">
                  차량별 배차 결과
                </caption>
                <thead>
                  <tr>
                    <th class="index-column">순번</th>
                    <th>경로 표시</th>
                    <th>차량 ID</th>
                    <th class="align-left">차량명</th>
                    <th>배송지 / 주문</th>
                    <th>예상 운행 시간</th>
                    <th>예상 주행거리 (km)</th>
                    <th>배송 중량 (kg)</th>
                    <th>적재율</th>
                  </tr>
                </thead>
                <tbody v-if="plans.length">
                  <tr class="total-row">
                    <th colspan="4">합계 <small>운행 시간은 차량별 합산</small></th>
                    <td>
                      {{ new Set(plans.flatMap((p) => p.orderList.map((o) => o.branchId))).size }}곳
                      / {{ totals.count }}건
                    </td>
                    <td>{{ duration(totals.time) }}</td>
                    <td>{{ number(totals.distance / 1000) }}</td>
                    <td>{{ number(totals.weight) }}</td>
                    <td>—</td>
                  </tr>
                  <tr
                    v-for="(plan, index) in plans"
                    :key="plan.vehicleId"
                    :class="{ 'active-row': state.activeVehicleId === plan.vehicleId }"
                  >
                    <td>{{ index + 1 }}</td>
                    <td>
                      <input
                        v-model="state.visibleVehicleIds"
                        type="checkbox"
                        :value="plan.vehicleId"
                        :aria-label="`${plan.vehicleName} 경로 표시`"
                        :style="{ accentColor: routeColors[index % routeColors.length] }"
                      />
                    </td>
                    <td class="vehicle-id">{{ plan.vehicleId }}</td>
                    <td class="align-left">
                      <button
                        class="vehicle-link"
                        :aria-pressed="state.activeVehicleId === plan.vehicleId"
                        @click="selectPlan(plan.vehicleId)"
                      >
                        <i :style="{ background: routeColors[index % routeColors.length] }" />{{
                          plan.vehicleName
                        }}<ArrowRight :size="12" />
                      </button>
                    </td>
                    <td>
                      {{ new Set(plan.orderList.map((o) => o.branchId)).size }}곳 /
                      {{ plan.deliveryCount }}건
                    </td>
                    <td>{{ duration(plan.deliveryTime) }}</td>
                    <td>{{ number(plan.deliveryDistance / 1000) }}</td>
                    <td>{{ number(plan.deliveryWeight) }}</td>
                    <td>
                      <span class="capacity-bar"
                        ><span
                          :style="{
                            width: `${Math.min(100, (plan.deliveryWeight / Number(data.vehicles.find((v) => v.vehicleId === plan.vehicleId)?.maxLoadKg)) * 100)}%`,
                            background: routeColors[index % routeColors.length],
                          }" /></span
                      >{{
                        Math.round(
                          (plan.deliveryWeight /
                            Number(
                              data.vehicles.find((v) => v.vehicleId === plan.vehicleId)?.maxLoadKg,
                            )) *
                            100,
                        )
                      }}%
                    </td>
                  </tr>
                </tbody>
                <tbody v-else>
                  <tr>
                    <td colspan="9" class="empty-result">
                      <div class="empty-result-content">
                        <LoaderCircle v-if="state.busy" class="spin" :size="21" /><Truck
                          v-else
                          :size="25"
                          :stroke-width="1.3"
                        /><span>{{
                          state.busy
                            ? '배차를 계산하고 있습니다. 잠시만 기다려 주세요.'
                            : state.result
                              ? '배정된 차량이 없습니다. 아래 미배차 사유를 확인해 주세요.'
                              : '배차를 요청하면 차량별 배송 결과가 표시됩니다.'
                        }}</span>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="detail-bar">
              <h3>
                배송지 상세
                <span v-if="activePlan"
                  >{{ activePlan.vehicleName }} · {{ activePlan.deliveryCount }}건</span
                >
              </h3>
              <button
                :disabled="!activePlan"
                :aria-expanded="detailsOpen"
                aria-controls="delivery-details"
                @click="detailsOpen = !detailsOpen"
              >
                {{ detailsOpen ? '접기' : '배송 순서 보기'
                }}<ChevronUp v-if="detailsOpen" :size="14" /><ChevronDown v-else :size="14" />
              </button>
            </div>
            <div
              v-if="detailsOpen && activePlan"
              id="delivery-details"
              class="table-scroll detail-scroll"
            >
              <table class="result-table detail-table">
                <caption class="sr-only">
                  {{
                    activePlan.vehicleName
                  }}
                  배송 순서
                </caption>
                <thead>
                  <tr>
                    <th>순서</th>
                    <th class="align-left">배송지 / 품목</th>
                    <th class="align-left">배송지 주소</th>
                    <th>중량 (kg)</th>
                    <th>작업 (분)</th>
                    <th>납품 희망</th>
                    <th>예상 도착</th>
                    <th>예상 출발</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(order, index) in activePlan.orderList" :key="order.orderId">
                    <td>
                      <span class="stop-number">{{ index + 1 }}</span>
                    </td>
                    <td class="align-left">{{ order.orderName }}</td>
                    <td class="align-left">{{ order.address }}</td>
                    <td>{{ order.deliveryWeight }}</td>
                    <td>{{ order.serviceTime }}</td>
                    <td>{{ order.desiredDeliveryTime }}</td>
                    <td>{{ arrival(order.expectedArrivalTime) }}</td>
                    <td>{{ arrival(order.expectedDepartureTime) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <details v-if="state.result?.mock.unassigned.length" class="unassigned" open>
              <summary>미배차 {{ state.result.mock.unassigned.length }}건 · 사유 확인</summary>
              <ul>
                <li v-for="order in state.result.mock.unassigned" :key="order.orderId">
                  <strong>{{ order.orderName }}</strong
                  ><span>{{ order.reason }}</span>
                </li>
              </ul>
            </details>
          </div>
        </section>
      </aside>
      <div class="map-column">
        <DeliveryMap
          :center="center"
          :orders="orders"
          :plans="plans"
          :visible-ids="state.visibleVehicleIds"
          :active-id="state.activeVehicleId"
          :has-result="!!state.result"
          @select="selectPlan"
        />
        <footer class="console-footer">
          <span>BADARO <span>배송을 잇다, 바다로.</span></span
          ><span>목업 데이터 · 직선 거리와 시속 30km 기준 · 납품 희망시간은 참고용</span>
        </footer>
      </div>
    </main>
    <DispatchProgressModal
      :open="state.modalOpen"
      :busy="state.busy"
      :elapsed="state.elapsed"
      :phase="state.phase"
      :error="state.error"
      :snapshot="state.snapshot"
      @close="state.modalOpen = false"
      @cancel="consoleState.cancel"
      @retry="consoleState.run"
    />
  </div>
</template>
