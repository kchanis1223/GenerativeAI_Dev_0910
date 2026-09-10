import { onMounted, onUnmounted, ref } from 'vue'

export function useReducedMotion() {
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
  const reducedMotion = ref(preference.matches)
  const sync = () => {
    reducedMotion.value = preference.matches
  }
  onMounted(() => preference.addEventListener('change', sync))
  onUnmounted(() => preference.removeEventListener('change', sync))
  return reducedMotion
}
