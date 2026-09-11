<script setup lang="ts">
import { oceanTransition } from '../composables/oceanTransition'
import waterPhoto from '../asset/water-surface.jpg'
</script>

<template>
  <div
    v-if="oceanTransition.active"
    class="ocean-transition"
    aria-hidden="true"
    :style="{ '--ocean-photo': `url('${waterPhoto}')` }"
  >
    <div class="ocean-split split-left"></div>
    <div class="ocean-split split-right"></div>
    <div class="ocean-wake"></div>
    <div class="ocean-mist"></div>
  </div>
</template>

<style scoped>
.ocean-transition {
  position: fixed;
  inset: 0;
  z-index: 1000;
  overflow: hidden;
  perspective: 700px;
  pointer-events: all;
}
.ocean-split {
  position: absolute;
  inset: -6%;
  background-image: var(--ocean-photo);
  background-size: cover;
  background-position: center;
  will-change: transform, opacity;
}
.split-left {
  clip-path: polygon(0 0, 51% 0, 49% 22%, 53% 43%, 49% 63%, 51% 82%, 48% 100%, 0 100%);
  animation: ocean-left 1.25s cubic-bezier(0.3, 0.02, 0.45, 1) both;
}
.split-right {
  clip-path: polygon(50% 0, 100% 0, 100% 100%, 47% 100%, 50% 82%, 48% 63%, 52% 43%, 48% 22%);
  animation: ocean-right 1.25s cubic-bezier(0.3, 0.02, 0.45, 1) both;
}
.ocean-wake {
  position: absolute;
  inset: -20% 49%;
  background: var(--background);
  border-radius: 50%;
  filter: blur(17px);
  box-shadow: 0 0 80px 22px var(--accent-200);
  animation: ocean-wake 1.25s ease-in both;
}
.ocean-mist {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, var(--accent-200) 0%, transparent 67%);
  animation: ocean-mist 1.25s both;
}
@keyframes ocean-left {
  0% {
    transform: scale(1);
  }
  35% {
    transform: translateX(-4%) scale(1.25);
  }
  100% {
    transform: translateX(-85%) translateZ(260px) scale(1.7);
    opacity: 0;
  }
}
@keyframes ocean-right {
  0% {
    transform: scale(1);
  }
  35% {
    transform: translateX(4%) scale(1.25);
  }
  100% {
    transform: translateX(85%) translateZ(260px) scale(1.7);
    opacity: 0;
  }
}
@keyframes ocean-wake {
  0% {
    transform: scaleX(0);
    opacity: 0;
  }
  35% {
    opacity: 0.85;
    transform: scaleX(2);
  }
  75% {
    transform: scaleX(25);
    opacity: 0.5;
  }
  100% {
    transform: scaleX(50);
    opacity: 0;
  }
}
@keyframes ocean-mist {
  0%,
  20% {
    opacity: 0;
    transform: scale(0.3);
  }
  60% {
    opacity: 0.75;
  }
  100% {
    opacity: 0;
    transform: scale(2);
  }
}
@media (prefers-reduced-motion: reduce) {
  .ocean-transition {
    display: none;
  }
}
</style>
