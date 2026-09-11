<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { callTms, tmsState } from '../stores/tms'
import type { DispatchResult, TmsPayload, VehiclePlan } from '../types/tms'
const allocationType = ref('1')
const selectedVehicles = ref(
  tmsState.vehicles.filter((v) => v.inputYn !== '0').map((v) => String(v.vehicleId)),
)
const selectedOrders = ref(tmsState.orders.map((v) => String(v.orderId)))
const startTime = ref('09:00')
const optionType = ref('1')
const equalizationType = ref('1')
const centerReturnYn = ref('Y')
const routeYn = ref('Y')
const phase = ref<'idle' | 'requesting' | 'polling' | 'done' | 'error'>('idle')
const busy = computed(() => phase.value === 'requesting' || phase.value === 'polling')
const mappingKey = ref('')
const result = ref<DispatchResult | null>(null)
const error = ref('')
const requestSnapshot = ref<TmsPayload | null>(null)
const stale = ref(false)
const activeVehicle = ref('')
const active = computed(() =>
  result.value?.vehicleList.find((v) => v.vehicleId === activeVehicle.value),
)
const routed = computed(() =>
  result.value?.vehicleRouteList?.find((v) => v.vehicleId === activeVehicle.value),
)
const totalCount = computed(
  () => result.value?.vehicleList.reduce((sum, v) => sum + v.deliveryCount, 0) ?? 0,
)
let disposed = false
onBeforeUnmount(() => {
  disposed = true
})
watch(
  [
    () => tmsState.vehicles,
    () => tmsState.orders,
    () => tmsState.centers,
    () => tmsState.banLines,
    allocationType,
    selectedVehicles,
    selectedOrders,
    startTime,
    optionType,
    equalizationType,
    centerReturnYn,
    routeYn,
  ],
  () => {
    if (result.value) stale.value = true
  },
  { deep: true },
)
async function run() {
  if (busy.value) return
  result.value = null
  error.value = ''
  mappingKey.value = ''
  phase.value = 'requesting'
  stale.value = false
  const request: TmsPayload = {
    allocationType: allocationType.value,
    startTime: startTime.value.replace(':', ''),
    optionType: optionType.value,
    equalizationType: equalizationType.value,
    centerReturnYn: centerReturnYn.value,
  }
  if (allocationType.value === '2') {
    request.vehicleIdList = selectedVehicles.value.join(',')
    request.orderIdList = selectedOrders.value.join(',')
  }
  requestSnapshot.value = request
  const includeRoutes = routeYn.value
  try {
    const receipt = await callTms('/allocation', request)
    if (disposed) return
    if (receipt.resultCode !== '200') throw new Error(String(receipt.resultMessage))
    mappingKey.value = String(receipt.mappingKey)
    phase.value = 'polling'
    for (let attempt = 0; attempt < 8; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 400))
      if (disposed) return
      const data = await callTms('/allocationData', {
        mappingKey: mappingKey.value,
        routeYn: includeRoutes,
      })
      if (disposed) return
      if (data.resultCode === '102') continue
      if (data.resultCode !== '200') throw new Error(String(data.resultMessage))
      result.value = data as unknown as DispatchResult
      activeVehicle.value =
        [...result.value.vehicleList].sort((a, b) => b.deliveryDistance - a.deliveryDistance)[0]
          ?.vehicleId ?? ''
      phase.value = 'done'
      return
    }
    throw new Error('결과 조회 시간이 초과되었습니다. 다시 요청해 주세요.')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '배차 요청 실패'
    phase.value = 'error'
  }
}
function routePoints(plan?: VehiclePlan) {
  if (!plan) return []
  const coordinates = plan.routeList.flatMap((r) =>
    r.route.split('|').map((pair) => pair.split(',').map(Number)),
  )
  const lng = coordinates.map((c) => c[0]!),
    lat = coordinates.map((c) => c[1]!)
  const minX = Math.min(...lng),
    maxX = Math.max(...lng),
    minY = Math.min(...lat),
    maxY = Math.max(...lat)
  const scale = Math.min(580 / (maxX - minX || 0.01), 230 / (maxY - minY || 0.01))
  return coordinates.map((c, i) => ({
    x: 350 + (c[0]! - (minX + maxX) / 2) * scale,
    y: 155 - (c[1]! - (minY + maxY) / 2) * scale,
    label: i === 0 ? '출발' : i > plan.orderList.length ? '도착' : String(i),
  }))
}
const points = computed(() => routePoints(routed.value))
const polyline = computed(() => points.value.map((p) => `${p.x},${p.y}`).join(' '))
function eta(value: string) {
  return `${value.slice(4, 6)}/${value.slice(6, 8)} ${value.slice(8, 10)}:${value.slice(10, 12)}`
}
</script>
<template>
  <section class="tms-card">
    <div class="tms-section-heading">
      <div>
        <h2>배차 조건 설정</h2>
        <p>투입 차량과 배송지, 출발 시간, 적재 기준을 설정하세요.</p>
      </div>
      <span class="tms-count">01</span>
    </div>
    <form @submit.prevent="run">
      <fieldset :disabled="busy" class="dispatch-fieldset">
        <div class="tms-fields">
          <label
            >배차 대상<select v-model="allocationType">
              <option value="1">전체 등록 정보</option>
              <option value="2">차량·배송지 직접 선택</option>
            </select></label
          >
          <label>출발 시간<input v-model="startTime" type="time" required /></label>
          <label
            >배차 기준<select v-model="optionType">
              <option value="1">중량 기준</option>
              <option value="2">부피 기준</option>
              <option value="3">배송지 수 기준</option>
            </select></label
          >
          <label
            >균등화 기준<select v-model="equalizationType">
              <option value="1">적용 안 함</option>
              <option value="2">거리 균등화</option>
              <option value="3">시간 균등화</option>
            </select></label
          >
          <label
            >센터 복귀<select v-model="centerReturnYn">
              <option value="Y">복귀</option>
              <option value="N">복귀 안 함</option>
            </select></label
          >
          <label
            >경로 데이터<select v-model="routeYn" aria-label="경로 데이터">
              <option value="Y">포함 · routeYn Y</option>
              <option value="N">제외 · routeYn N</option>
            </select></label
          >
        </div>
        <div v-if="allocationType === '2'" class="dispatch-selection">
          <div>
            <h3>투입 차량 · {{ selectedVehicles.length }}</h3>
            <label v-for="v in tmsState.vehicles" :key="v.vehicleId"
              ><input
                v-model="selectedVehicles"
                type="checkbox"
                :value="String(v.vehicleId)"
                :disabled="v.inputYn === '0'"
              />{{ v.vehicleName }}
              <small>{{ v.weight }} ton {{ v.inputYn === '0' ? '· 투입 제외' : '' }}</small></label
            >
          </div>
          <div>
            <h3>배송지 · {{ selectedOrders.length }}</h3>
            <label v-for="o in tmsState.orders" :key="o.orderId"
              ><input v-model="selectedOrders" type="checkbox" :value="String(o.orderId)" />{{
                o.orderName
              }}
              <small>{{ o.deliveryWeight }} kg</small></label
            >
          </div>
        </div>
        <p class="tms-notice">
          출발 센터: {{ tmsState.centers[0]?.centerName ?? '센터를 등록해 주세요' }} · 차량
          {{ tmsState.vehicles.filter((v) => v.inputYn !== '0').length }}대 투입 가능 · 배송지
          {{ tmsState.orders.length }}곳
        </p>
        <button class="tms-primary dispatch-submit" :disabled="busy">
          {{ busy ? '배차 처리 중…' : '배차 요청하기' }} <span aria-hidden="true">→</span>
        </button>
      </fieldset>
    </form>
    <p v-if="error" role="alert" class="tms-notice error">{{ error }}</p>
  </section>
  <section class="tms-card" aria-live="polite">
    <div class="tms-section-heading">
      <div>
        <h2>배차 결과</h2>
        <p>요청 → mappingKey 발급 → 결과 조회</p>
      </div>
      <span class="tms-count">02</span>
    </div>
    <ol class="dispatch-progress">
      <li :class="{ complete: !!mappingKey }">배차 요청</li>
      <li :class="{ complete: !!mappingKey }">키 발급</li>
      <li :class="{ complete: phase === 'done' }">
        결과 조회{{ phase === 'polling' ? ' 중…' : '' }}
      </li>
    </ol>
    <p v-if="mappingKey" class="mapping-key">
      mappingKey <code>{{ mappingKey }}</code>
    </p>
    <p v-if="stale" class="tms-notice">
      조건이 변경되었습니다. 아래는 이전 요청의 결과이며, 다시 배차하면 갱신됩니다.
    </p>
    <p v-if="phase === 'idle'" class="tms-empty">
      배차 조건을 설정하고 요청하면 결과가 표시됩니다.
    </p>
    <template v-if="result">
      <div class="dispatch-totals">
        <div>
          <strong>{{ result.vehicleCount }}</strong
          ><span>배차 차량</span>
        </div>
        <div>
          <strong>{{ totalCount }}</strong
          ><span>배차 배송지</span>
        </div>
        <div>
          <strong>{{ result.mock.unassigned.length }}</strong
          ><span>미배차 배송지</span>
        </div>
      </div>
      <div v-if="result.vehicleList.length" class="route-results">
        <label class="tms-label"
          >차량별 배송 순서<select v-model="activeVehicle">
            <option v-for="v in result.vehicleList" :key="v.vehicleId" :value="v.vehicleId">
              {{ v.vehicleName }} · {{ v.deliveryCount }}곳
            </option>
          </select></label
        >
        <template v-if="active"
          ><div class="route-metrics">
            <span>{{ active.deliveryWeight }} kg</span><span>{{ active.deliveryVolume }} cbm</span
            ><span>약 {{ (active.deliveryDistance / 1000).toFixed(1) }} km</span
            ><span>약 {{ Math.ceil(active.deliveryTime / 60) }}분</span>
          </div>
          <figure v-if="routed" class="route-diagram">
            <svg viewBox="0 0 700 310" role="img" aria-label="배송 순서 직선 경로도">
              <defs>
                <pattern id="route-grid" width="35" height="35" patternUnits="userSpaceOnUse">
                  <path d="M 35 0 L 0 0 0 35" fill="none" stroke="#cde5e8" stroke-width="1" />
                </pattern>
              </defs>
              <rect width="700" height="310" fill="url(#route-grid)" />
              <polyline
                :points="polyline"
                fill="none"
                stroke="#087f95"
                stroke-width="3"
                stroke-linejoin="round"
              />
              <g v-for="(p, i) in points" :key="i">
                <circle
                  :cx="p.x"
                  :cy="p.y"
                  r="16"
                  :fill="i === 0 ? '#17343d' : '#087f95'"
                  stroke="white"
                  stroke-width="3"
                />
                <text :x="p.x" :y="p.y + 4" fill="white" text-anchor="middle" font-size="11">
                  {{ p.label }}
                </text>
              </g>
            </svg>
            <figcaption>직선 연결 시연도 · 실제 도로 경로가 아닙니다.</figcaption>
          </figure>
          <p v-else class="tms-notice">경로 데이터 제외로 요청하여 배송 순서만 표시합니다.</p>
          <ol class="delivery-stops">
            <li v-for="(o, i) in active.orderList" :key="o.orderId">
              <span>{{ i + 1 }}</span>
              <div>
                <strong>{{ o.orderName }}</strong>
                <p>{{ o.address }}</p>
                <small>{{ o.deliveryWeight }} kg · 작업 {{ o.serviceTime }}분</small>
              </div>
              <div class="stop-time">
                도착 {{ eta(o.expectedArrivalTime)
                }}<small>출발 {{ eta(o.expectedDepartureTime) }}</small>
              </div>
            </li>
          </ol>
        </template>
      </div>
      <div v-if="result.mock.unassigned.length" class="unassigned">
        <h3>미배차 배송지</h3>
        <p v-for="o in result.mock.unassigned" :key="o.orderId">
          <strong>{{ o.orderName }}</strong
          ><span>{{ o.reason }}</span>
        </p>
      </div>
      <details class="api-details">
        <summary>목업 계산 기준</summary>
        <p>{{ result.mock.routing }}</p>
        <ul>
          <li v-for="assumption in result.mock.assumptions" :key="assumption">{{ assumption }}</li>
        </ul>
        <p>
          차종과 권역을 맞추고 적재 한도를 검사한 뒤 가까운 배송지부터 순서대로 배분합니다. 실제
          TMS의 최적화 알고리즘과는 다릅니다.
        </p>
      </details>
      <details class="api-details">
        <summary>요청·결과 JSON</summary>
        <pre>{{ JSON.stringify(requestSnapshot, null, 2) }}</pre>
        <pre>{{ JSON.stringify(result, null, 2) }}</pre>
      </details>
    </template>
  </section>
</template>
