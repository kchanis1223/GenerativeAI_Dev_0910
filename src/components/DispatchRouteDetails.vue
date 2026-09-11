<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { DispatchResult, VehiclePlan } from '../types/tms'
const props = defineProps<{ result: DispatchResult }>()
const activeVehicle = ref('')
watch(
  () => props.result,
  (result) => {
    activeVehicle.value =
      [...result.vehicleList].sort((a, b) => b.deliveryDistance - a.deliveryDistance)[0]
        ?.vehicleId ?? ''
  },
  { immediate: true },
)
const active = computed(() =>
  props.result.vehicleList.find((v) => v.vehicleId === activeVehicle.value),
)
const routed = computed(() =>
  props.result.vehicleRouteList?.find((v) => v.vehicleId === activeVehicle.value),
)
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
  <p v-else class="tms-empty">
    배차된 차량이 없습니다. 미배차 사유를 확인하고 조건을 변경해 주세요.
  </p>
</template>
