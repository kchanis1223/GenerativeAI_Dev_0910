import { ref } from 'vue'
import type { RunRecord } from '../types'

// Keep query history when navigating to vehicle, order, and dispatch routes.
export const centerHistory = ref<RunRecord[]>([])
