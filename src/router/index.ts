import { createRouter, createWebHistory } from 'vue-router'
import LandingView from '../views/LandingView.vue'

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: LandingView },
    {
      path: '/workspace',
      name: 'dispatch',
      component: () => import('../views/DispatchConsoleView.vue'),
    },
    { path: '/owner', name: 'owner', component: () => import('../views/OwnerView.vue') },
    { path: '/workspace/:pathMatch(.*)*', redirect: '/workspace' },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
router.afterEach((to) => {
  document.title =
    to.name === 'home'
      ? 'Badaro'
      : to.name === 'owner'
        ? '점주님 · Badaro'
        : '본사물류운영자 · Badaro'
})
