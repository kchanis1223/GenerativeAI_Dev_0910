<script setup lang="ts">
import { ref } from 'vue'
import { MessageSquare, ArrowUp } from '@lucide/vue'

defineProps<{
  centerName: string
  vehicleCount: number
  orderCount: number
}>()

const draft = ref('')
</script>

<template>
  <section class="agent-chat" aria-labelledby="agent-chat-title">
    <header class="chat-header">
      <h2 id="agent-chat-title"><MessageSquare :size="20" />배차 에이전트</h2>
      <span id="chat-connection-status" class="chat-status">연결 준비 중</span>
    </header>
    <div class="chat-context" aria-label="현재 선택 정보">
      <span>{{ centerName }}</span>
      <span>차량 {{ vehicleCount }}대</span>
      <span>주문 {{ orderCount }}건</span>
    </div>

    <div class="chat-composer">
      <label for="agent-message" class="sr-only">에이전트 메시지</label>
      <textarea
        id="agent-message"
        v-model="draft"
        rows="3"
        maxlength="2000"
        placeholder="예: 오전 9시에 출발하고, 활어 배송을 먼저 확인해줘."
        aria-describedby="chat-connection-status"
      />
      <div class="chat-composer-footer">
        <span>입력 초안 · {{ draft.length }} / 2,000</span>
        <button type="button" disabled aria-label="메시지 전송 (에이전트 연결 준비 중)">
          <ArrowUp :size="19" />
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.agent-chat {
  border: 1px solid #cfdfe2;
  border-radius: 8px;
  background: linear-gradient(145deg, #f0f8f8, #fff 65%);
  padding: 28px;
  margin-bottom: 28px;
  min-width: 0;
  color: #29464d;
}
.chat-header,
.chat-header h2,
.chat-context,
.chat-composer-footer {
  display: flex;
  align-items: center;
  gap: 10px;
}
.chat-header {
  justify-content: space-between;
  flex-wrap: wrap;
}
.chat-header h2 {
  color: #176775;
  font-size: 20px;
}
.chat-status {
  padding: 5px 9px;
  border-radius: 20px;
  background: #e8efef;
  color: #596f75;
  font-size: 13px;
}
.chat-context {
  flex-wrap: wrap;
  gap: 6px 12px;
  margin-top: 15px;
  font-size: 13px;
  color: #59757c;
}
.chat-composer {
  margin-top: 32px;
  border: 1px solid #bdd4d8;
  border-radius: 8px;
  padding: 16px;
  background: white;
}
.chat-composer:focus-within {
  outline: 2px solid #278f9d;
  outline-offset: 2px;
}
.chat-composer textarea {
  display: block;
  width: 100%;
  min-height: 78px;
  max-height: 200px;
  resize: vertical;
  border: 0;
  outline: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 16px;
  line-height: 1.6;
}
.chat-composer textarea::placeholder {
  color: #788c92;
}
.chat-composer-footer {
  justify-content: space-between;
  margin-top: 10px;
  font-size: 12px;
  color: #657b82;
}
.chat-composer-footer button {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 6px;
  background: #e3eeee;
  color: #80999d;
  cursor: not-allowed;
}
@media (max-width: 540px) {
  .agent-chat {
    padding: 20px;
  }
}
</style>
