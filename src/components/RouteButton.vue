<script setup lang="ts">
import { ArrowRight } from '@lucide/vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'

defineProps<{ to: RouteLocationRaw }>()
</script>

<template>
  <RouterLink :to="to" class="route-button">
    <span><slot /></span>
    <ArrowRight :size="17" :stroke-width="1.5" aria-hidden="true" />
  </RouterLink>
</template>

<style scoped>
.route-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 29px;
  min-width: 162px;
  min-height: 48px;
  padding: 12px 24px;
  border: 1px solid rgb(239 255 255 / 48%);
  border-radius: 999px;
  background: rgb(25 77 89 / 13%);
  color: #f0ffff;
  font-size: 15px;
  font-weight: 400;
  letter-spacing: 0.08em;
  backdrop-filter: blur(8px);
  transition:
    background 0.3s,
    border-color 0.3s,
    transform 0.3s;
}
.route-button:hover {
  background: rgb(237 255 255 / 18%);
  border-color: rgb(239 255 255 / 80%);
  transform: translateY(-2px);
}
.route-button svg {
  transition: transform 0.3s;
}
.route-button:hover svg {
  transform: translateX(4px);
}
.route-button:focus-visible {
  outline: 2px solid white;
  outline-offset: 6px;
}
@media (prefers-reduced-motion: reduce) {
  .route-button,
  .route-button svg {
    transition: none;
  }
}
</style>
