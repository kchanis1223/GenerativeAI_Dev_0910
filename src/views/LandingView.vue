<script setup lang="ts">
import JumpingFish from '../components/JumpingFish.vue'
import BadaroLogo from '../components/BadaroLogo.vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { enterWorkspace, oceanTransition } from '../composables/oceanTransition'
import WaterSurface from '../components/WaterSurface.vue'
import { useReducedMotion } from '../composables/useReducedMotion'

const reduceMotion = useReducedMotion()
const router = useRouter()
const navigationError = ref('')
async function enter(event: MouseEvent) {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
  event.preventDefault()
  navigationError.value = ''
  try {
    await enterWorkspace(router)
  } catch {
    navigationError.value = '화면을 열지 못했습니다. 로고를 눌러 다시 시도해 주세요.'
  }
}
</script>

<template>
  <main class="landing" :class="{ entering: oceanTransition.active }" aria-label="Badaro">
    <WaterSurface />
    <JumpingFish />
    <svg class="wordmark-filter" aria-hidden="true" width="0" height="0">
      <defs>
        <filter
          id="badaro-ripple"
          x="-15%"
          y="-25%"
          width="130%"
          height="150%"
          color-interpolation-filters="sRGB"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency=".009 .025"
            numOctaves="2"
            seed="3"
            result="water-noise"
          >
            <animate
              v-if="!reduceMotion"
              attributeName="baseFrequency"
              values=".009 .025;.012 .019;.008 .023;.009 .025"
              dur="12s"
              repeatCount="indefinite"
            />
          </feTurbulence>
          <feDisplacementMap
            in="SourceGraphic"
            in2="water-noise"
            :scale="reduceMotion ? 0 : 9"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </defs>
    </svg>
    <div class="landing-content">
      <h1 class="badaro-wordmark" aria-label="Badaro">
        <a
          :href="router.resolve('/workspace').href"
          class="logo-entry"
          aria-label="바다로 워크스페이스 입장"
          :aria-disabled="oceanTransition.active"
          @click="enter"
          ><BadaroLogo decorative priority
        /></a>
      </h1>
      <p v-if="navigationError" class="navigation-error" role="alert">{{ navigationError }}</p>
    </div>
  </main>
</template>

<style scoped>
.landing {
  --font-ui: 'SSRO WaterDrop', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
  font-family: var(--font-ui);
  position: relative;
  isolation: isolate;
  display: grid;
  place-items: center;
  width: 100%;
  min-height: 100svh;
  max-width: none;
  margin: 0;
  padding: 32px 24px;
  overflow: hidden;
  background: #5797a1;
}
.landing::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(ellipse at 50% 45%, rgb(3 37 47 / 8%) 25%, rgb(3 37 47 / 24%) 100%);
}
.wordmark-filter {
  position: absolute;
  pointer-events: none;
}
.landing-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: clamp(40px, 6vh, 65px);
  margin-top: 0;
}
.badaro-wordmark {
  display: block;
  margin: 0;
  color: #e5f5f2;
  font-family: var(--font-ui);
  width: min(760px, 80vw);
  max-width: 100%;
  font-weight: 400;
  line-height: 1.1;
  letter-spacing: -0.045em;
  padding: 0;
  filter: url(#badaro-ripple);
}
.badaro-wordmark :deep(.badaro-logo) {
  animation: wordmark-drift 9s ease-in-out infinite;
  filter: drop-shadow(0 0 1px rgb(230 255 255 / 90%)) drop-shadow(0 3px 12px rgb(226 253 253 / 60%));
}
.logo-entry {
  display: block;
  cursor: pointer;
  border-radius: 22px;
  transition: transform 0.35s ease;
}
.logo-entry:hover {
  transform: scale(1.035);
}
.logo-entry:focus-visible {
  outline: 2px solid #dcffff;
  outline-offset: 16px;
}
.entering .landing-content {
  opacity: 0;
  transform: scale(1.25);
  transition:
    opacity 0.3s,
    transform 0.65s;
  pointer-events: none;
}
.navigation-error {
  color: white;
  font-family: 'JayeonSans', sans-serif;
  font-size: 14px;
}
@keyframes wordmark-drift {
  0%,
  100% {
    transform: translateY(-3px) rotate(-0.3deg);
  }
  50% {
    transform: translateY(4px) rotate(0.3deg);
  }
}
@media (max-width: 540px) {
  .landing-content {
    gap: 45px;
    margin-top: 0;
  }
  .badaro-wordmark {
    width: 88vw;
  }
}
@media (prefers-reduced-motion: reduce) {
  .badaro-wordmark :deep(.badaro-logo) {
    animation: none;
  }
  .logo-entry {
    transition: none;
  }
  .logo-entry:hover {
    transform: none;
  }
  .badaro-wordmark {
    animation: none;
    filter: none;
  }
}
</style>
