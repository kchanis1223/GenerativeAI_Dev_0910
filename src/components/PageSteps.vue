<script setup lang="ts">
defineProps<{ items: { label: string; target: string }[]; active: number }>()
defineEmits<{ select: [index: number] }>()
</script>

<template>
  <nav class="page-steps" aria-label="페이지 구간 이동">
    <a
      v-for="(item, index) in items"
      :key="item.target"
      :href="`#${item.target}`"
      :class="{ active: active === index }"
      :aria-current="active === index ? 'location' : undefined"
      @click.prevent="$emit('select', index)"
    >
      <span>{{ item.label }}</span>
    </a>
  </nav>
</template>
