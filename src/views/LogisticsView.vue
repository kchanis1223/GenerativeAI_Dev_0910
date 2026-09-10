<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import WorkspaceHeader from '../components/WorkspaceHeader.vue'
import TmsResources from '../components/TmsResources.vue'
import TmsExplorer from '../components/TmsExplorer.vue'
import TmsDispatch from '../components/TmsDispatch.vue'
import { tmsLogs, tmsState } from '../stores/tms'
import '../logistics.css'
const route = useRoute()
const section = computed(() => String(route.params.section))
const pages: Record<string, { title: string; intro: string; steps: string[] }> = {
  vehicles: {
    title: '차량 정보 관리',
    intro: '배송의 시작, 차량과 적재 정보를 준비하세요.',
    steps: ['차량 정보', '배송지 정보', '배차 요청', '결과 확인'],
  },
  orders: {
    title: '배송지 정보 관리',
    intro: '배송할 장소와 물량을 한곳에서 관리하세요.',
    steps: ['차량 정보', '배송지 정보', '배차 요청', '결과 확인'],
  },
  dispatch: {
    title: '배차 요청하기',
    intro: '준비된 정보를 연결해 배송 흐름을 그려보세요.',
    steps: ['차량 정보', '배송지 정보', '배차 요청', '결과 확인'],
  },
  api: {
    title: 'API 살펴보기',
    intro: '요청부터 응답까지, 물류 데이터가 움직이는 과정.',
    steps: ['API 선택', '요청 구성', '목업 실행', '응답 확인'],
  },
}
const page = computed(() => pages[section.value]!)
const stepIndex = computed(() =>
  section.value === 'orders' ? 1 : section.value === 'dispatch' ? 2 : 0,
)
const latest = computed(() => tmsLogs[0])
</script>
<template>
  <div class="workspace-page logistics-page">
    <WorkspaceHeader />
    <main>
      <section class="workspace-hero">
        <div class="page-container">
          <h1>{{ page.title }}</h1>
          <p class="logistics-intro">{{ page.intro }}</p>
          <ol class="logistics-steps">
            <li v-for="(label, i) in page.steps" :key="label" :class="{ active: i === stepIndex }">
              <span>{{ label }}</span>
            </li>
          </ol>
        </div>
      </section>
      <div class="logistics-body">
        <div class="page-container logistics-grid">
          <div class="logistics-content">
            <TmsResources
              v-if="section === 'vehicles' || section === 'orders'"
              :initial="section"
            /><TmsDispatch v-else-if="section === 'dispatch'" /><TmsExplorer v-else />
          </div>
          <aside class="logistics-summary">
            <h2>준비된 정보</h2>
            <dl>
              <div>
                <dt>서비스 이름</dt>
                <dd>바다로</dd>
              </div>
              <div>
                <dt>센터</dt>
                <dd>{{ tmsState.centers.length }}곳</dd>
              </div>
              <div>
                <dt>권역</dt>
                <dd>{{ tmsState.zones.length }}개</dd>
              </div>
              <div>
                <dt>차량</dt>
                <dd>{{ tmsState.vehicles.length }}대</dd>
              </div>
              <div>
                <dt>배송지</dt>
                <dd>{{ tmsState.orders.length }}곳</dd>
              </div>
              <div>
                <dt>교차금지선</dt>
                <dd>{{ tmsState.banLines.length }}개</dd>
              </div>
            </dl>
            <div class="summary-total">
              <span>투입 가능 차량</span
              ><strong>{{ tmsState.vehicles.filter((v) => v.inputYn !== '0').length }}대</strong>
            </div>
            <p class="tms-notice">
              목업 데이터로 동작합니다.<br />변경 내용은 새로고침하면 초기화됩니다.
            </p>
            <RouterLink to="/workspace/dispatch" class="tms-primary summary-link"
              >배차 요청하기 <span>→</span></RouterLink
            ><RouterLink to="/workspace/api" class="summary-api"
              >24개 API 예제 살펴보기 ↗</RouterLink
            >
            <div v-if="latest" class="summary-latest">
              <small>최근 API 실행 · {{ latest.time }}</small>
              <p>{{ latest.title }}</p>
              <span :class="['log-state', latest.status]">{{ latest.status }}</span>
            </div>
          </aside>
        </div>
      </div>
    </main>
    <footer class="logistics-footer">
      <RouterLink to="/">Badaro</RouterLink><span>물류의 흐름을, 바다로.</span
      ><small>SK TMS Open API · 프론트엔드 데모</small>
    </footer>
  </div>
</template>
