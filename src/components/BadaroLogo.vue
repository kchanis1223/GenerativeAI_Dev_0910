<script setup lang="ts">
import logo from '../asset/badaro-logo.png'

withDefaults(defineProps<{ decorative?: boolean; priority?: boolean }>(), {
  decorative: false,
  priority: false,
})
</script>

<template>
  <img
    :src="logo"
    :alt="decorative ? '' : '바다로 · Badaro'"
    :aria-hidden="decorative || undefined"
    :fetchpriority="priority ? 'high' : 'auto'"
    width="2042"
    height="690"
    class="badaro-logo"
    decoding="async"
  />
</template>

<style scoped>
.badaro-logo {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
}
</style>
