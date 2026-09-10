import { createRouter, createWebHistory } from 'vue-router'
import LandingView from '../views/LandingView.vue'

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: LandingView },
    {
      path: '/workspace/:page(flow|history)?',
      name: 'workspace',
      component: () => import('../views/WorkspaceView.vue'),
    },
    {
      path: '/workspace/:section(vehicles|orders|dispatch|api)',
      name: 'logistics',
      component: () => import('../views/LogisticsView.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition ?? { top: 0 }
  },
})

router.afterEach((to) => {
  const labels: Record<string, string> = {
    vehicles: '차량 정보',
    orders: '배송지 정보',
    dispatch: '배차 요청',
    api: 'API 탐색',
  }
  const section =
    labels[String(to.params.section)] ??
    (to.params.page === 'flow'
      ? '동작 흐름'
      : to.params.page === 'history'
        ? '실행 기록'
        : '센터 워크스페이스')
  document.title = to.name === 'home' ? 'Badaro' : `${section} · Badaro`
})
