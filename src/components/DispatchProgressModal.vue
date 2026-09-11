<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { X, LoaderCircle, Check, ArrowRight } from '@lucide/vue'
import { number } from '../services/dispatch-display'
const props = defineProps<{
  open: boolean
  busy: boolean
  elapsed: number
  phase: 'request' | 'calculating'
  error: string
  snapshot: {
    centerName: string
    vehicles: number
    orders: number
    branches: number
    weight: number
    returnToCenter: boolean
  } | null
}>()
const emit = defineEmits<{ close: []; cancel: []; retry: [] }>()
const dialog = ref<HTMLDialogElement>()
watch(
  () => props.open,
  async (open) => {
    await nextTick()
    if (open && !dialog.value?.open) dialog.value?.showModal()
    if (!open && dialog.value?.open) dialog.value.close()
  },
  { immediate: true },
)
onBeforeUnmount(() => dialog.value?.close())
</script>

<template>
  <dialog
    ref="dialog"
    class="dispatch-modal"
    aria-labelledby="progress-title"
    @cancel.prevent="emit('close')"
  >
    <header class="modal-header">
      <h2 id="progress-title">배차 요청 <LoaderCircle v-if="busy" class="spin" :size="18" /></h2>
      <button class="icon-button" aria-label="배차 창 닫기" @click="emit('close')">
        <X :size="22" />
      </button>
    </header>
    <div class="modal-body">
      <div class="progress-heading">
        <span class="eyebrow">{{ snapshot?.centerName }}</span>
        <h3>{{ error ? '배차 요청을 확인해 주세요' : '배송의 순서를 계산하고 있어요' }}</h3>
        <p>선택한 차량과 주문으로 배송 경로를 구성합니다.</p>
      </div>
      <table class="request-table">
        <caption class="sr-only">
          배차 요청 정보
        </caption>
        <thead>
          <tr>
            <th>배송 차량</th>
            <th>배송지 / 주문</th>
            <th>총 배송 중량</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <strong>{{ snapshot?.vehicles }}</strong> 대
            </td>
            <td>
              <strong>{{ snapshot?.branches }}</strong> 곳 /
              <strong>{{ snapshot?.orders }}</strong> 건
            </td>
            <td>
              <strong>{{ number(snapshot?.weight ?? 0) }}</strong> kg
            </td>
          </tr>
        </tbody>
      </table>
      <p class="return-info">
        <Check :size="15" />
        {{ snapshot?.returnToCenter ? '배송 완료 후 센터로 복귀' : '마지막 배송지에서 운행 종료' }}
      </p>
      <div class="request-progress" aria-label="계산 진행 단계">
        <span class="done"><Check :size="15" /> 선택 정보 확인</span><ArrowRight :size="14" />
        <span :class="{ done: phase === 'calculating' }"
          >{{ phase === 'calculating' ? '배차 계산 중' : '배차 요청 중'
          }}<LoaderCircle v-if="busy" class="spin" :size="15"
        /></span>
      </div>
      <div v-if="error" class="modal-error" role="alert">{{ error }}</div>
      <div v-else class="elapsed-time">
        <span>배차 중 · 경과 시간</span
        ><strong
          >{{ String(Math.floor(elapsed / 60)).padStart(2, '0') }}<small>분</small>
          {{ String(elapsed % 60).padStart(2, '0') }}<small>초</small></strong
        >
        <div class="indeterminate"><span /></div>
      </div>
      <p class="modal-caption">
        {{
          error
            ? '설정을 확인하거나 다시 시도해 주세요.'
            : '계산이 완료되면 이 화면에서 결과를 바로 보여드립니다.'
        }}
      </p>
      <footer class="modal-footer">
        <button v-if="busy" class="plain-button" @click="emit('cancel')">배차 취소</button
        ><button v-else class="primary-button" @click="emit('retry')">다시 요청</button
        ><button class="soft-button" @click="emit('close')">닫기</button>
      </footer>
      <p v-if="busy" class="modal-footnote">창을 닫아도 계산은 계속됩니다.</p>
    </div>
  </dialog>
</template>
