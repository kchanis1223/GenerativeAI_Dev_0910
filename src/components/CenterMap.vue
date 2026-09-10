<script setup lang="ts">
import { computed, ref } from 'vue'
import { LocateFixed, Minus, Plus } from '@lucide/vue'
import type { Center } from '../types'

const props = defineProps<{ centers: Center[]; selectedId: string | null }>()
const emit = defineEmits<{ select: [id: string] }>()
const zoom = ref(1)
const points = computed(() => {
  if (!props.centers.length) return []
  const lats = props.centers.map((c) => c.latitude)
  const lngs = props.centers.map((c) => c.longitude)
  const minLat = Math.min(...lats),
    maxLat = Math.max(...lats)
  const minLng = Math.min(...lngs),
    maxLng = Math.max(...lngs)
  return props.centers.map((c) => ({
    ...c,
    x:
      110 + ((c.longitude - minLng) / (maxLng - minLng || 1)) * 570 + (maxLng === minLng ? 285 : 0),
    y: 80 + ((maxLat - c.latitude) / (maxLat - minLat || 1)) * 230 + (maxLat === minLat ? 115 : 0),
  }))
})
</script>

<template>
  <div class="center-map">
    <div class="map-caption">
      <span class="live-dot"></span> 센터 위치 <span>좌표 기반 개략도</span>
    </div>
    <svg
      viewBox="0 0 800 380"
      class="map-canvas"
      role="group"
      aria-label="센터 좌표 개략도. 배경은 실제 지도가 아닙니다."
    >
      <defs>
        <pattern
          id="map-grid"
          width="45"
          height="45"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(-18)"
        >
          <rect width="45" height="45" fill="#e9f1f4" />
          <path d="M 45 0 H 0 V 45" fill="none" stroke="#fcfefe" stroke-width="5" />
          <rect x="8" y="8" width="29" height="29" rx="4" fill="#e1eaf0" opacity=".6" />
        </pattern>
      </defs>
      <rect width="800" height="380" fill="url(#map-grid)" />
      <path
        d="M0 65Q120 90 160 0H0ZM510 0Q500 80 610 78T800 135V0ZM0 300Q120 270 135 380H0ZM540 380Q530 270 670 305T800 280V380"
        fill="#d4e5ea"
        opacity=".85"
      />
      <path
        d="M-20 214C100 135 160 180 246 235S390 302 472 226 620 162 820 205"
        fill="none"
        stroke="#f7fcfd"
        stroke-width="51"
      />
      <path
        d="M-20 214C100 135 160 180 246 235S390 302 472 226 620 162 820 205"
        fill="none"
        stroke="#abd2e0"
        stroke-width="37"
      />
      <g stroke="#fbfdfe" stroke-width="8" fill="none">
        <path d="M80 0 330 380M500 0 230 380M770 0 505 380M0 70 800 315M0 335 800 60" />
      </g>
      <g stroke="#d0e0e7" stroke-width="1" fill="none">
        <path d="M80 0 330 380M500 0 230 380M770 0 505 380M0 70 800 315M0 335 800 60" />
      </g>
      <g :transform="`translate(400 190) scale(${zoom}) translate(-400 -190)`">
        <g
          v-for="point in points"
          :key="point.centerId"
          :transform="`translate(${point.x} ${point.y})`"
          class="map-point"
          role="button"
          tabindex="0"
          :aria-label="`${point.centerName} 선택`"
          :aria-pressed="selectedId === point.centerId"
          @click="emit('select', point.centerId)"
          @keydown.enter.prevent="emit('select', point.centerId)"
          @keydown.space.prevent="emit('select', point.centerId)"
        >
          <circle v-if="selectedId === point.centerId" r="27" fill="#178298" opacity=".13" />
          <circle
            r="15"
            :fill="selectedId === point.centerId ? '#08788e' : '#ffffff'"
            stroke="#178298"
            stroke-width="2"
          />
          <path
            d="m-6 -3 6-4 6 4v8H-6Zm0 0 6 4 6-4M0 1v4"
            fill="none"
            :stroke="selectedId === point.centerId ? '#ddf5f7' : '#178298'"
            stroke-width="1.4"
          />
          <rect x="-39" y="21" width="78" height="23" rx="6" fill="#ffffff" stroke="#d8e9ef" />
          <text y="36" text-anchor="middle" fill="#315d70" font-size="11" font-weight="600">
            {{ point.centerName }}
          </text>
        </g>
      </g>
    </svg>
    <div v-if="!centers.length" class="map-empty">조회된 센터가 이곳에 표시됩니다.</div>
    <div class="map-controls">
      <button
        aria-label="위치 개략도 확대"
        :disabled="zoom >= 1.4"
        @click="zoom = Math.min(1.4, zoom + 0.2)"
      >
        <Plus :size="16" />
      </button>
      <button
        aria-label="위치 개략도 축소"
        :disabled="zoom <= 0.8"
        @click="zoom = Math.max(0.8, zoom - 0.2)"
      >
        <Minus :size="16" />
      </button>
      <button aria-label="위치 개략도 배율 초기화" @click="zoom = 1">
        <LocateFixed :size="16" />
      </button>
    </div>
    <div class="map-note">배경은 실제 지도가 아닙니다 · 데모 시각화</div>
  </div>
</template>
