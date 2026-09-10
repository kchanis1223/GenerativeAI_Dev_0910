<script setup lang="ts">
import waterPhoto from '../asset/물 표면.jpg'
import { useReducedMotion } from '../composables/useReducedMotion'

const reducedMotion = useReducedMotion()
</script>

<template>
  <div class="water-surface" aria-hidden="true">
    <svg class="water-filter" width="0" height="0">
      <defs>
        <filter
          id="water-surface-ripple"
          x="-10%"
          y="-10%"
          width="120%"
          height="120%"
          color-interpolation-filters="sRGB"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency=".008 .012"
            numOctaves="2"
            seed="7"
            result="surface-noise"
          >
            <animate
              v-if="!reducedMotion"
              attributeName="baseFrequency"
              values=".008 .012;.011 .009;.007 .014;.008 .012"
              dur="22s"
              repeatCount="indefinite"
            />
          </feTurbulence>
          <feDisplacementMap
            in="SourceGraphic"
            in2="surface-noise"
            :scale="reducedMotion ? 0 : 32"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </defs>
    </svg>
    <img :src="waterPhoto" alt="" class="water-photo" fetchpriority="high" decoding="async" />
  </div>
</template>

<style scoped>
.water-surface {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background: #07505f;
}
.water-filter {
  position: absolute;
  pointer-events: none;
}
.water-photo {
  position: absolute;
  inset: -5%;
  width: 110%;
  height: 110%;
  max-width: none;
  object-fit: cover;
  object-position: center;
  filter: url(#water-surface-ripple);
  animation: surface-drift 24s ease-in-out infinite;
}
@keyframes surface-drift {
  0%,
  100% {
    transform: translate(-0.5%, -0.5%) scale(1.01);
  }
  50% {
    transform: translate(0.5%, 0.7%) scale(1.04);
  }
}
@media (prefers-reduced-motion: reduce) {
  .water-photo {
    animation: none;
    filter: none;
  }
}
</style>
