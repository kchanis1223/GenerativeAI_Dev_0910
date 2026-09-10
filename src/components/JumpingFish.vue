<script setup lang="ts">
import { onMounted, onUnmounted, ref, useId } from 'vue'

const id = useId()
const hidden = ref(false)
const syncVisibility = () => {
  hidden.value = document.hidden
}
onMounted(() => {
  syncVisibility()
  document.addEventListener('visibilitychange', syncVisibility)
})
onUnmounted(() => document.removeEventListener('visibilitychange', syncVisibility))

const fish = [
  { x: '15%', y: '26%', duration: '7.2s', delay: '-.45s', mirrored: false },
  { x: '78%', y: '29%', duration: '8.4s', delay: '-3.1s', mirrored: true },
  { x: '23%', y: '82%', duration: '9.1s', delay: '-6.7s', mirrored: false },
]
</script>

<template>
  <div class="jumping-fish" :class="{ paused: hidden }" aria-hidden="true">
    <div
      v-for="(item, index) in fish"
      :key="index"
      class="fish-scene"
      :class="{ mirrored: item.mirrored }"
      :style="{ '--x': item.x, '--y': item.y, '--duration': item.duration, '--delay': item.delay }"
    >
      <div class="fish-waterline">
        <span class="fish-ripple ripple-one"></span>
        <span class="fish-ripple ripple-two"></span>
        <span class="fish-drop drop-one"></span>
        <span class="fish-drop drop-two"></span>
        <span class="fish-drop drop-three"></span>
      </div>
      <div class="fish-jump">
        <svg class="fish-body" viewBox="0 0 100 52" focusable="false">
          <defs>
            <linearGradient :id="`${id}-body-${index}`" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stop-color="#458f9d" />
              <stop offset=".42" stop-color="#b9e5e4" />
              <stop offset=".72" stop-color="#effaf5" />
              <stop offset="1" stop-color="#82c6d0" />
            </linearGradient>
            <linearGradient :id="`${id}-fin-${index}`" x1="0" y1="0" x2="1" y2="1">
              <stop stop-color="#c1edf0" stop-opacity=".95" />
              <stop offset="1" stop-color="#579eac" stop-opacity=".9" />
            </linearGradient>
          </defs>
          <g class="fish-tail">
            <path
              d="M30 24C20 19 10 9 4 10L10 26 4 42C15 39 23 32 30 28Z"
              :fill="`url(#${id}-fin-${index})`"
              stroke="#b6e6e9"
              stroke-width=".7"
            />
            <path
              d="M11 16 27 25M10 26H27M11 36 27 27"
              fill="none"
              stroke="#e4f6f1"
              stroke-opacity=".55"
              stroke-width=".7"
            />
          </g>
          <path d="M44 13 54 3Q65 5 71 14M48 38 59 48 67 37" :fill="`url(#${id}-fin-${index})`" />
          <path
            d="M24 26C38 6 73 6 95 25Q81 44 55 40C41 38 31 32 24 26Z"
            :fill="`url(#${id}-body-${index})`"
            stroke="#d3efee"
            stroke-width=".6"
          />
          <path
            d="M31 25Q60 13 87 24"
            fill="none"
            stroke="#efffff"
            stroke-opacity=".65"
            stroke-width="1.3"
          />
          <path
            d="M73 17Q67 27 74 35"
            fill="none"
            stroke="#599da9"
            stroke-opacity=".7"
            stroke-width="1"
          />
          <path d="M61 29 48 36 55 24Z" fill="#649fac" opacity=".8" />
          <g fill="none" stroke="#478d9f" stroke-opacity=".28" stroke-width=".7">
            <path d="M43 19q5 5 0 9m9-10q5 5 0 9m9-10q5 5 0 9M47 27q4 4 0 8m10-9q4 4 0 8" />
          </g>
          <circle cx="83" cy="22" r="2.8" fill="#e3f6f1" />
          <circle cx="83.3" cy="22" r="1.65" fill="#174c60" />
          <circle cx="83.8" cy="21.4" r=".55" fill="white" />
          <path d="m90 28 4-2" stroke="#397d8f" stroke-width=".8" />
        </svg>
      </div>
    </div>
  </div>
</template>

<style scoped>
.jumping-fish {
  position: absolute;
  inset: 0;
  z-index: 1;
  overflow: hidden;
  pointer-events: none;
  user-select: none;
  --jump-height: -80px;
}
.fish-scene {
  position: absolute;
  left: var(--x);
  top: var(--y);
  width: 150px;
  height: 70px;
}
.fish-scene.mirrored {
  transform: scaleX(-1);
}
.fish-jump {
  position: absolute;
  bottom: 18px;
  left: 0;
  width: 79px;
  opacity: 0;
  animation: fish-hop var(--duration) linear var(--delay) infinite;
}
.fish-body {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
  filter: drop-shadow(0 5px 5px rgb(0 40 58 / 28%));
  animation: fish-turn var(--duration) linear var(--delay) infinite;
}
.fish-tail {
  transform-box: view-box;
  transform-origin: 28px 26px;
  animation: tail-flick 0.17s ease-in-out infinite alternate;
}
.fish-waterline {
  position: absolute;
  width: 74px;
  height: 22px;
  left: 60px;
  bottom: 6px;
}
.fish-ripple {
  position: absolute;
  inset: 0;
  border: 1px solid rgb(218 251 251 / 70%);
  border-radius: 50%;
  opacity: 0;
  animation: landing-ripple var(--duration) linear var(--delay) infinite;
}
.ripple-two {
  inset: 4px 11px;
  animation-name: inner-ripple;
}
.fish-drop {
  position: absolute;
  width: 3px;
  height: 6px;
  left: 32px;
  top: 8px;
  background: #c8f1f0;
  border-radius: 70% 70% 50% 50%;
  opacity: 0;
  --drop-x: -21px;
  --drop-y: -25px;
  animation: water-droplet var(--duration) linear var(--delay) infinite;
}
.drop-two {
  --drop-x: 9px;
  --drop-y: -34px;
  width: 2px;
  height: 5px;
}
.drop-three {
  --drop-x: 28px;
  --drop-y: -20px;
  width: 3px;
  height: 4px;
}
@keyframes fish-hop {
  0%,
  2% {
    opacity: 0;
    transform: translate(0, 10px) scale(0.86);
  }
  4% {
    opacity: 0.95;
    transform: translate(5px, -12px) scale(0.95);
  }
  10% {
    opacity: 1;
    transform: translate(28px, var(--jump-height)) scale(1);
  }
  15% {
    opacity: 1;
    transform: translate(48px, -56px) scale(1);
  }
  21% {
    opacity: 0.9;
    transform: translate(68px, 0) scale(0.95);
  }
  23% {
    opacity: 0;
    transform: translate(72px, 10px) scale(0.85);
  }
  27% {
    opacity: 0;
    transform: translate(72px, 10px) scale(0.85);
  }
  30% {
    opacity: 0.9;
    transform: translate(74px, -16px) scale(0.88);
  }
  34% {
    opacity: 1;
    transform: translate(82px, -43px) scale(0.92);
  }
  39% {
    opacity: 0.9;
    transform: translate(95px, 0) scale(0.85);
  }
  42%,
  100% {
    opacity: 0;
    transform: translate(100px, 13px) scale(0.75);
  }
}
@keyframes fish-turn {
  0%,
  4% {
    transform: rotate(-42deg);
  }
  10% {
    transform: rotate(-13deg);
  }
  15% {
    transform: rotate(19deg);
  }
  21%,
  24% {
    transform: rotate(53deg);
  }
  27%,
  30% {
    transform: rotate(-44deg);
  }
  34% {
    transform: rotate(-6deg);
  }
  39%,
  100% {
    transform: rotate(48deg);
  }
}
@keyframes tail-flick {
  from {
    transform: rotate(-11deg) scaleX(0.82);
  }
  to {
    transform: rotate(11deg) scaleX(1);
  }
}
@keyframes landing-ripple {
  0%,
  20% {
    opacity: 0;
    transform: scale(0.35);
  }
  23% {
    opacity: 0.65;
    transform: scale(0.55);
  }
  33% {
    opacity: 0;
    transform: scale(1.7);
  }
  38% {
    opacity: 0;
    transform: translateX(27px) scale(0.35);
  }
  41% {
    opacity: 0.5;
    transform: translateX(27px) scale(0.65);
  }
  53%,
  100% {
    opacity: 0;
    transform: translateX(27px) scale(1.8);
  }
}
@keyframes inner-ripple {
  0%,
  22% {
    opacity: 0;
    transform: scale(0.4);
  }
  25% {
    opacity: 0.45;
    transform: scale(0.7);
  }
  35% {
    opacity: 0;
    transform: scale(1.9);
  }
  40% {
    opacity: 0;
    transform: translateX(27px) scale(0.4);
  }
  43% {
    opacity: 0.4;
    transform: translateX(27px) scale(0.7);
  }
  55%,
  100% {
    opacity: 0;
    transform: translateX(27px) scale(1.9);
  }
}
@keyframes water-droplet {
  0%,
  20% {
    opacity: 0;
    transform: translate(0, 0) scale(0.5);
  }
  23% {
    opacity: 0.75;
    transform: translate(var(--drop-x), var(--drop-y)) scale(1);
  }
  28%,
  37% {
    opacity: 0;
    transform: translate(var(--drop-x), 6px) scale(0.6);
  }
  40% {
    opacity: 0.6;
    transform: translate(calc(var(--drop-x) + 27px), var(--drop-y)) scale(0.9);
  }
  46%,
  100% {
    opacity: 0;
    transform: translate(calc(var(--drop-x) + 27px), 6px) scale(0.5);
  }
}
.paused *,
.paused *::before,
.paused *::after {
  animation-play-state: paused !important;
}
@media (max-width: 600px) {
  .jumping-fish {
    --jump-height: -60px;
  }
  .fish-scene {
    width: 115px;
    height: 50px;
  }
  .fish-scene:nth-child(1) {
    left: 8%;
    top: 24%;
  }
  .fish-scene:nth-child(2) {
    left: auto;
    right: 7%;
    top: 79%;
  }
  .fish-scene:nth-child(3) {
    display: none;
  }
  .fish-jump {
    width: 55px;
  }
  .fish-waterline {
    width: 56px;
    height: 17px;
    left: 46px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .jumping-fish {
    display: none;
  }
  .jumping-fish * {
    animation: none;
  }
}
</style>
