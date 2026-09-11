<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { MessageSquare, ArrowUp } from '@lucide/vue'
import {
  agentHealth,
  sendAgentMessage,
  modeLabels,
  type AgentMode,
  type AgentReply,
} from '../services/agent'

const draft = ref('')
const busy = ref(false)
const connecting = ref(false)
const mode = ref<AgentMode>()
const error = ref('')
const threadId = ref<string>()
const finished = ref(false)
const messages = ref<{ text: string; reply?: AgentReply }[]>([])
async function connect() {
  connecting.value = true
  error.value = ''
  try {
    mode.value = await agentHealth()
  } catch {
    mode.value = undefined
    error.value =
      '에이전트 서버에 연결할 수 없습니다. Python 서버를 실행한 뒤 연결 확인을 누르세요.'
  } finally {
    connecting.value = false
  }
}
onMounted(connect)
function reset() {
  threadId.value = undefined
  finished.value = false
  messages.value = []
  draft.value = ''
  error.value = ''
}
async function send() {
  const text = draft.value.trim()
  if (!text || busy.value || finished.value || !mode.value) return
  busy.value = true
  error.value = ''
  messages.value.push({ text })
  draft.value = ''
  try {
    const reply = await sendAgentMessage(text, threadId.value)
    threadId.value = reply.thread_id
    mode.value = reply.mode
    finished.value = reply.status !== 'needs_clarification'
    messages.value.push({ text: reply.message, reply })
  } catch (cause) {
    // A lost response may still have executed dispatch. Never resend automatically.
    finished.value = true
    error.value = `${cause instanceof Error ? cause.message : '서버 응답을 받지 못했습니다.'} 실행 여부를 확인한 뒤 새 대화를 시작하세요. 자동 재전송하지 않습니다.`
  } finally {
    busy.value = false
  }
}
const resultLabels = { success: '배차 성공', partial: '일부 배차', failed: '배차 실패' }
</script>

<template>
  <section class="agent-chat" aria-labelledby="agent-chat-title">
    <header class="chat-header">
      <h2 id="agent-chat-title"><MessageSquare :size="20" />배차 에이전트</h2>
      <span id="chat-connection-status" class="chat-status" role="status">{{
        busy ? '요청 처리 중' : mode ? modeLabels[mode] : '서버 연결 안 됨'
      }}</span>
    </header>
    <p class="chat-context">
      본사 운영자 로컬 시연 · 배차 조건은 메시지에 입력하세요. 아래 프론트 목업 선택값과 지도는
      에이전트에 연결되지 않습니다.
    </p>
    <p v-if="mode === 'offline'" class="chat-context">
      예: 마포 서대문 은평 배차해줘 → 배송일 질문에 2026-09-11 입력. 시간 변경·재배차는 지원하지
      않습니다.
    </p>
    <div class="chat-context">
      <button type="button" :disabled="busy || connecting" @click="connect">연결 확인</button>
      <button type="button" :disabled="busy" @click="reset">새 대화</button>
    </div>
    <div class="chat-messages" role="log" aria-label="에이전트 대화" aria-live="polite">
      <article v-for="(entry, index) in messages" :key="index">
        <strong>{{ entry.reply ? '에이전트' : '사용자' }}</strong>
        <p>{{ entry.text }}</p>
        <template v-if="entry.reply">
          <small>{{ modeLabels[entry.reply.mode] }} · 요청 {{ entry.reply.request_id }}</small>
          <ul v-if="entry.reply.questions.length">
            <li v-for="q in entry.reply.questions" :key="q">{{ q }}</li>
          </ul>
          <p v-if="entry.reply.error" role="alert">
            {{ entry.reply.error.code }} · {{ entry.reply.error.message }}
          </p>
          <section v-if="entry.reply.result" aria-label="Python 배차 결과">
            <h3>{{ resultLabels[entry.reply.result.status] }}</h3>
            <p v-if="!entry.reply.result.routes.length">배정된 차량이 없습니다.</p>
            <div v-for="(route, routeIndex) in entry.reply.result.routes" :key="routeIndex">
              <h4>차량 {{ route.vehicle_id }}</h4>
              <p>
                거리 {{ route.distance_meters === null ? '미제공' : `${route.distance_meters}m` }} ·
                소요시간
                {{
                  route.estimated_duration_seconds === null
                    ? '미제공'
                    : `${route.estimated_duration_seconds}초`
                }}
              </p>
              <div class="table-scroll">
                <table>
                  <caption class="sr-only">
                    {{
                      route.vehicle_id
                    }}
                    방문 순서
                  </caption>
                  <thead>
                    <tr>
                      <th>순서</th>
                      <th>지점 ID</th>
                      <th>주문 ID</th>
                      <th>품목</th>
                      <th>ETA</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(stop, stopIndex) in route.stops" :key="stopIndex">
                      <td>{{ stop.sequence }}</td>
                      <td>{{ stop.destination_id }}</td>
                      <td>{{ stop.order_id }}</td>
                      <td>미제공</td>
                      <td>{{ stop.eta ?? '미제공' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <h4>미배정 {{ entry.reply.result.unassigned_orders.length }}건</h4>
            <ul>
              <li
                v-for="(order, orderIndex) in entry.reply.result.unassigned_orders"
                :key="orderIndex"
              >
                {{ order.order_id }} · {{ order.reason_code ?? '사유 코드 미제공' }} ·
                {{ order.reason_message ?? '사유 미제공' }}
              </li>
            </ul>
          </section>
        </template>
      </article>
    </div>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="finished" class="chat-context">
      요청이 종료됐습니다. 다른 요청은 새 대화로 시작하세요.
    </p>
    <form class="chat-composer" @submit.prevent="send">
      <label for="agent-message" class="sr-only">에이전트 메시지</label>
      <textarea
        id="agent-message"
        v-model="draft"
        rows="3"
        maxlength="2000"
        :disabled="busy || finished"
        placeholder="마포 서대문 은평 배차해줘"
        aria-describedby="chat-connection-status"
      />
      <div class="chat-composer-footer">
        <span>{{ draft.length }} / 2,000</span>
        <button
          type="submit"
          :disabled="!draft.trim() || busy || finished || !mode"
          aria-label="메시지 전송"
        >
          <ArrowUp :size="19" />
        </button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.agent-chat {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  padding: 28px;
  margin-bottom: 28px;
  min-width: 0;
  color: var(--text-primary);
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
  color: var(--primary-600);
  font-size: 20px;
}
.chat-status {
  padding: 5px 9px;
  border-radius: 20px;
  background: var(--selection);
  color: var(--text-secondary);
  font-size: 13px;
}
.chat-context {
  flex-wrap: wrap;
  gap: 6px 12px;
  margin-top: 15px;
  font-size: 13px;
  color: var(--text-secondary);
}
.chat-composer {
  margin-top: 32px;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  background: var(--surface);
}
.chat-composer:focus-within {
  outline: 2px solid var(--primary-600);
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
  color: var(--text-secondary);
}
.chat-composer-footer {
  justify-content: space-between;
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-secondary);
}
.chat-composer-footer button {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 6px;
  background: var(--border);
  color: var(--text-secondary);
  cursor: not-allowed;
}
.chat-messages {
  max-height: 580px;
  overflow: auto;
  overflow-wrap: anywhere;
}
.chat-messages article {
  border-top: 1px solid var(--border);
  padding: 16px 0;
}
.chat-messages p {
  white-space: pre-wrap;
  margin: 8px 0;
}
.chat-messages table {
  border-collapse: collapse;
  min-width: 480px;
  font-size: 14px;
}
.chat-messages th,
.chat-messages td {
  padding: 8px;
  border: 1px solid var(--border);
  text-align: left;
}
.chat-context button {
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 6px 10px;
}
.chat-composer-footer button:not(:disabled) {
  background: var(--primary-600);
  color: white;
  cursor: pointer;
}
@media (max-width: 540px) {
  .agent-chat {
    padding: 20px;
  }
}
</style>
