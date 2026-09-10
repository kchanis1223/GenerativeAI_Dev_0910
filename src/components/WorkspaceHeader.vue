<script setup lang="ts">
import { useRoute, useRouter, RouterLink } from 'vue-router'
import BadaroLogo from './BadaroLogo.vue'
const route = useRoute()
const router = useRouter()
const links = [
  { path: '/workspace', label: '센터 워크스페이스' },
  { path: '/workspace/vehicles', label: '차량 정보' },
  { path: '/workspace/orders', label: '배송지 정보' },
  { path: '/workspace/dispatch', label: '배차 요청' },
  { path: '/workspace/api', label: 'API 탐색' },
  { path: '/workspace/flow', label: '동작 흐름' },
  { path: '/workspace/history', label: '실행 기록' },
]
</script>
<template>
  <header class="site-header">
    <div class="site-header-inner expanded-header">
      <RouterLink to="/" class="brand" aria-label="Badaro 메인 페이지"
        ><BadaroLogo decorative
      /></RouterLink>
      <nav class="main-navigation" aria-label="메인 메뉴">
        <button
          v-for="link in links"
          :key="link.path"
          :class="{ active: route.path === link.path }"
          :aria-current="route.path === link.path ? 'page' : undefined"
          @click="router.push(link.path)"
        >
          {{ link.label }}
        </button>
      </nav>
      <div class="header-actions">
        <slot><span class="mock-badge">MOCK DEMO</span></slot>
      </div>
    </div>
  </header>
</template>
<style scoped>
.expanded-header {
  gap: 22px;
}
.expanded-header .main-navigation {
  gap: 20px;
}
.expanded-header .main-navigation button {
  font-size: 14px;
  white-space: nowrap;
}
.mock-badge {
  color: var(--ocean);
  background: var(--ocean-light);
  padding: 12px 16px;
  border-radius: 30px;
  font-size: 12px;
  white-space: nowrap;
}
@media (max-width: 1200px) {
  .site-header {
    height: auto;
  }
  .expanded-header {
    flex-wrap: wrap;
    padding-block: 16px;
  }
  .expanded-header .main-navigation {
    order: 3;
    width: 100%;
    overflow-x: auto;
    padding-bottom: 6px;
  }
}
</style>
