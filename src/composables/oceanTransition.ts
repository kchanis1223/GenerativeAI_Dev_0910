import { reactive } from 'vue'
import type { Router } from 'vue-router'

export const oceanTransition = reactive({ active: false })
const pause = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export async function enterWorkspace(
  router: Router,
  destination: '/workspace' | '/owner' = '/workspace',
) {
  if (oceanTransition.active) return
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    await router.push(destination)
    return
  }
  oceanTransition.active = true
  try {
    await pause(650)
    await router.push(destination)
    await pause(600)
  } finally {
    oceanTransition.active = false
  }
}
