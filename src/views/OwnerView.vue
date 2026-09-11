<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { Truck, Package } from '@lucide/vue'
import BadaroLogo from '../components/BadaroLogo.vue'
</script>

<template>
  <div class="owner-page">
    <header class="console-header">
      <RouterLink to="/" class="console-brand" aria-label="Badaro 메인 페이지"
        ><BadaroLogo priority
      /></RouterLink>
      <span class="header-divider" />
      <h1>점주님 페이지</h1>
      <RouterLink to="/" class="owner-back">진입 화면으로</RouterLink>
    </header>
    <main class="owner-content">
      <h2>차량·배송정보 등록</h2>
      <p>등록 화면과 API 연결을 준비 중입니다.</p>
      <div class="owner-options">
        <section
          v-for="item in [
            {
              name: '차량 등록',
              icon: Truck,
              description: '차량명, 적재량, 운송 가능한 품목을 등록합니다.',
            },
            {
              name: '배송정보 등록',
              icon: Package,
              description: '배송지 주소, 품목, 중량, 납품 희망시간을 등록합니다.',
            },
          ]"
          :key="item.name"
        >
          <component :is="item.icon" :size="28" aria-hidden="true" />
          <h3>{{ item.name }}</h3>
          <p>{{ item.description }}</p>
          <button disabled type="button">등록 준비 중</button>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.owner-page {
  min-height: 100dvh;
  background: var(--background);
}
.owner-back {
  margin-left: auto;
  font-size: 14px;
  color: var(--text-secondary);
}
.owner-content {
  max-width: 1100px;
  margin: 0 auto;
  padding: 64px 32px;
}
.owner-content h2 {
  font-size: 28px;
  color: var(--primary-800);
}
.owner-content p {
  margin-top: 14px;
  color: var(--text-secondary);
  line-height: 1.8;
}
.owner-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 28px;
  margin-top: 40px;
}
.owner-options section {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 32px;
  background: var(--surface);
  color: var(--primary-600);
}
.owner-options h3 {
  font-size: 21px;
  margin-top: 24px;
  color: var(--text-primary);
}
.owner-options button {
  margin-top: 32px;
  padding: 12px 20px;
  border-radius: 6px;
  background: var(--selection);
  color: var(--text-secondary);
  cursor: not-allowed;
}
@media (max-width: 650px) {
  .owner-content {
    padding: 40px 20px;
  }
  .owner-options {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  .owner-options section {
    padding: 24px;
  }
}
</style>
