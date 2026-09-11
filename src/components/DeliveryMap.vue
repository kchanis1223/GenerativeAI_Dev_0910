<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { TmsRow, VehiclePlan } from '../types/tms'
import { arrival, routeColors } from '../services/dispatch-display'

const props = defineProps<{
  center?: TmsRow
  orders: TmsRow[]
  plans: VehiclePlan[]
  visibleIds: string[]
  activeId: string
  hasResult: boolean
}>()
const emit = defineEmits<{ select: [id: string] }>()
const element = ref<HTMLElement>()
const tileError = ref(false)
let map: L.Map | undefined
let layer: L.LayerGroup | undefined
let resize: ResizeObserver | undefined
let routeLayers: { id: string; path: L.Polyline }[] = []
let stopMarkers: { id: string; marker: L.Marker }[] = []
const visiblePlans = computed(() =>
  props.plans.filter((p) => props.visibleIds.includes(p.vehicleId)),
)
const point = (row: TmsRow | { latitude: string; longitude: string }): L.LatLngTuple => [
  Number(row.latitude),
  Number(row.longitude),
]
function popup(title: string, lines: string[]) {
  const el = document.createElement('div')
  const heading = document.createElement('strong')
  heading.textContent = title
  el.append(heading)
  for (const line of lines) {
    const text = document.createElement('div')
    text.textContent = line
    el.append(text)
  }
  return el
}
function frame() {
  if (!map) return
  const points: L.LatLngTuple[] = props.center ? [point(props.center)] : []
  const rows = props.hasResult ? visiblePlans.value.flatMap((p) => p.orderList) : props.orders
  points.push(...rows.map(point))
  if (points.length)
    map.fitBounds(L.latLngBounds(points), { padding: [65, 65], maxZoom: 13, animate: false })
}
function draw() {
  if (!map || !layer) return
  layer.clearLayers()
  routeLayers = []
  stopMarkers = []
  if (props.center) {
    L.marker(point(props.center), {
      title: String(props.center.centerName),
      icon: L.divIcon({
        className: 'center-pin',
        html: '<span>센터</span>',
        iconSize: [50, 40],
        iconAnchor: [25, 40],
      }),
      zIndexOffset: 1000,
    })
      .bindPopup(popup(String(props.center.centerName), [String(props.center.address)]))
      .addTo(layer)
  }
  if (!props.hasResult) {
    const groups = new Map<string, TmsRow[]>()
    for (const order of props.orders) {
      const key = String(order.branchId)
      groups.set(key, [...(groups.get(key) ?? []), order])
    }
    for (const group of groups.values()) {
      const order = group[0]!
      L.circleMarker(point(order), {
        radius: 8,
        color: 'white',
        weight: 2,
        fillColor: '#3D97B4',
        fillOpacity: 0.85,
      })
        .bindPopup(
          popup(String(order.orderName).split('·')[0]!, [
            String(order.address),
            `${group.length}건 · ${group.map((o) => o.itemName).join(', ')}`,
          ]),
        )
        .addTo(layer)
    }
  }
  for (const plan of visiblePlans.value) {
    const color =
      routeColors[
        props.plans.findIndex((p) => p.vehicleId === plan.vehicleId) % routeColors.length
      ]!
    for (const segment of plan.routeList ?? []) {
      const points = segment.route.split('|').map((s): L.LatLngTuple => {
        const [lng, lat] = s.split(',').map(Number)
        return [lat!, lng!]
      })
      const path = L.polyline(points, {
        color,
        weight: props.activeId === plan.vehicleId ? 4 : 3,
        opacity: 0.8,
        dashArray: '8 5',
      })
        .on('click', () => emit('select', plan.vehicleId))
        .addTo(layer)
      routeLayers.push({ id: plan.vehicleId, path })
    }
    const groups = new Map<string, { order: TmsRow; stops: number[]; times: string[] }>()
    plan.orderList.forEach((order, index) => {
      const key = `${order.latitude},${order.longitude}`
      const group = groups.get(key) ?? { order, stops: [], times: [] }
      group.stops.push(index + 1)
      group.times.push(`${index + 1}. ${order.itemName} · ${arrival(order.expectedArrivalTime)}`)
      groups.set(key, group)
    })
    for (const group of groups.values()) {
      const badge = document.createElement('span')
      badge.style.backgroundColor = color
      badge.textContent = group.stops.join('·')
      const marker = L.marker(point(group.order), {
        title: `${plan.vehicleName} · 배송 ${group.stops.join('·')}`,
        icon: L.divIcon({
          className: 'delivery-pin',
          html: badge,
          iconSize: [36, 36],
          iconAnchor: [18, 36],
        }),
        zIndexOffset: props.activeId === plan.vehicleId ? 500 : 0,
      })
        .bindPopup(popup(plan.vehicleName, [String(group.order.address), ...group.times]))
        .on('click', () => emit('select', plan.vehicleId))
        .addTo(layer)
      stopMarkers.push({ id: plan.vehicleId, marker })
    }
  }
  highlight()
}
function highlight() {
  for (const { id, path } of routeLayers) {
    path.setStyle({ weight: id === props.activeId ? 4 : 3 })
    if (id === props.activeId) path.bringToFront()
  }
  for (const { id, marker } of stopMarkers) {
    marker.setZIndexOffset(id === props.activeId ? 500 : 0)
  }
}
onMounted(() => {
  if (!element.value) return
  map = L.map(element.value, { zoomControl: false, scrollWheelZoom: false }).setView(
    [37.55, 126.98],
    12,
  )
  L.control.zoom({ position: 'bottomright' }).addTo(map)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
  })
    .on('tileerror', () => {
      tileError.value = true
    })
    .addTo(map)
  layer = L.layerGroup().addTo(map)
  resize = new ResizeObserver(() => map?.invalidateSize({ pan: false }))
  resize.observe(element.value)
  draw()
  frame()
})
watch(
  () => [props.center, props.orders, props.plans, props.visibleIds, props.hasResult],
  () => {
    draw()
    frame()
  },
  { deep: true },
)
watch(() => props.activeId, highlight)
onBeforeUnmount(() => {
  resize?.disconnect()
  map?.remove()
})
</script>

<template>
  <section class="map-region" aria-label="배송 경로 지도">
    <div ref="element" class="delivery-map" aria-label="서울 배송 지도" />
    <button class="map-fit" @click="frame">전체 위치 보기 <span aria-hidden="true">⌖</span></button>
    <div v-if="hasResult && plans.length" class="map-legend" aria-label="차량 경로 범례">
      <button
        v-for="(plan, index) in plans"
        :key="plan.vehicleId"
        :class="{
          muted: !visibleIds.includes(plan.vehicleId),
          selected: activeId === plan.vehicleId,
        }"
        :aria-pressed="activeId === plan.vehicleId"
        @click="emit('select', plan.vehicleId)"
      >
        <i :style="{ background: routeColors[index % routeColors.length] }" />{{ plan.vehicleName }}
      </button>
    </div>
    <p v-if="tileError" class="map-error" role="status">
      배경 지도를 불러오지 못했습니다. 배송 위치와 경로는 계속 확인할 수 있습니다.
    </p>
    <p class="map-disclaimer">
      {{
        hasResult
          ? '점선은 목업 직선 경로입니다. 실제 도로 경로와 다릅니다.'
          : '노량진센터 출발 · 서울 지점의 실제 주소 기준'
      }}
    </p>
  </section>
</template>
