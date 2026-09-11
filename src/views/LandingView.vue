<script setup lang="ts">
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
    navigationError.value = '화면을 열지 못했습니다. 진입 버튼을 눌러 다시 시도해 주세요.'
  }
}
</script>

<template>
  <main class="landing" :class="{ entering: oceanTransition.active }" aria-label="Badaro">
    <WaterSurface />
    <svg class="wordmark-filter" aria-hidden="true" width="0" height="0">
      <defs>
        <filter
          id="badaro-outline"
          x="-15%"
          y="-25%"
          width="130%"
          height="150%"
          color-interpolation-filters="sRGB"
        >
          <feMorphology in="SourceAlpha" operator="dilate" radius="1.25" result="expanded" />
          <feComposite in="expanded" in2="SourceAlpha" operator="out" result="edge" />
          <feFlood flood-color="#f0ffff" flood-opacity=".85" />
          <feComposite in2="edge" operator="in" result="outline" />
          <feMerge>
            <feMergeNode in="outline" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
          <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#002e3c" flood-opacity=".8" />
        </filter>
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
        <BadaroLogo decorative priority />
      </h1>
      <nav class="entry-options" aria-label="본사 운영자 페이지 진입">
        <a
          :href="router.resolve('/workspace').href"
          class="role-entry operator-entry"
          :aria-disabled="oceanTransition.active"
          @click="enter($event)"
          >본사물류운영자 페이지 진입 <span aria-hidden="true">↗</span></a
        >
      </nav>
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
  background: var(--primary-800);
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
  max-width: 100%;
}
.badaro-wordmark {
  display: block;
  margin: 0;
  color: #e5f5f2;
  font-family: var(--font-ui);
  width: min(800px, 80vw);
  max-width: 100%;
  font-weight: 400;
  line-height: 1.1;
  letter-spacing: -0.045em;
  padding: 0;
  filter: url(#badaro-ripple);
  mix-blend-mode: luminosity;
}
.badaro-wordmark :deep(.badaro-logo) {
  animation: wordmark-drift 9s ease-in-out infinite;
  filter: brightness(1.15) url(#badaro-outline);
}
.entry-options {
  display: flex;
  justify-content: center;
  gap: clamp(24px, 5vw, 72px);
  padding: 12px;
  max-width: 100%;
}
.role-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  min-height: 76px;
  padding: 20px 28px;
  border: 1px solid var(--accent-200);
  border-radius: 18px;
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  box-shadow:
    0 14px 32px #002c3c38,
    inset 0 1px 0 #ffffff;
  color: var(--primary-800);
  font-family: 'JayeonSans', sans-serif;
  font-size: clamp(17px, 1.6vw, 22px);
  text-decoration: none;
  backdrop-filter: blur(10px);
  animation: entry-drift 11s ease-in-out infinite;
  transition:
    background 0.25s,
    box-shadow 0.25s;
}
.operator-entry {
  animation-delay: -5s;
  animation-duration: 13s;
}
.role-entry span {
  font-size: 26px;
}
.role-entry:hover {
  background: var(--surface);
  box-shadow: 0 18px 40px #002c3c55;
}
.role-entry:hover,
.role-entry:focus-visible {
  animation-play-state: paused;
}
.role-entry:focus-visible {
  outline: 3px solid white;
  outline-offset: 7px;
}
@keyframes entry-drift {
  0%,
  100% {
    transform: translate(-4px, -5px) rotate(-0.6deg);
  }
  50% {
    transform: translate(5px, 7px) rotate(0.6deg);
  }
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
  color: var(--surface);
  font-family: 'JayeonSans', sans-serif;
  font-size: 14px;
}
@keyframes wordmark-drift {
  0%,
  100% {
    transform: translate(-5px, -7px) rotate(-0.4deg);
  }
  50% {
    transform: translate(5px, 7px) rotate(0.4deg);
  }
}
@media (max-width: 540px) {
  .landing {
    padding-inline: 16px;
  }
  .entry-options {
    flex-direction: column;
    width: min(340px, 100%);
    gap: 24px;
  }
  .role-entry {
    min-height: 68px;
    padding: 18px 20px;
    gap: 16px;
  }
  .landing-content {
    gap: 45px;
    margin-top: 0;
  }
  .badaro-wordmark {
    width: min(92vw, calc(100vw - 32px));
  }
}
@media (prefers-reduced-motion: reduce) {
  .badaro-wordmark :deep(.badaro-logo) {
    animation: none;
  }
  .role-entry {
    animation: none;
    transition: none;
  }
  .badaro-wordmark {
    animation: none;
    filter: none;
  }
}
</style>
