<script setup lang="ts">
withDefaults(defineProps<{ size?: number; colorA?: string; colorB?: string }>(), {
  size: 20,
  colorA: '#8fb0d4',
  colorB: '#b4b8bf',
})

// Gear path: teeth on a pitch radius, evenodd center hole. `offsetDeg` rotates tooth 0.
function gearPath(cx: number, cy: number, teeth: number, pitch: number, offsetDeg: number): string {
  const outer = pitch + 1.2
  const root = pitch - 1.4
  const step = 360 / teeth
  const pt = (r: number, deg: number) => {
    const a = (deg * Math.PI) / 180
    return `${(cx + r * Math.cos(a)).toFixed(2)} ${(cy + r * Math.sin(a)).toFixed(2)}`
  }
  const parts: string[] = []
  for (let i = 0; i < teeth; i++) {
    const a = offsetDeg + i * step
    parts.push(
      `${i === 0 ? 'M' : 'L'}${pt(root, a - 0.3 * step)}`,
      `L${pt(outer, a - 0.17 * step)}`,
      `L${pt(outer, a + 0.17 * step)}`,
      `L${pt(root, a + 0.3 * step)}`,
    )
  }
  const hole = pitch * 0.35
  return `${parts.join(' ')} Z M${cx + hole} ${cy} A${hole} ${hole} 0 1 0 ${cx - hole} ${cy} A${hole} ${hole} 0 1 0 ${cx + hole} ${cy} Z`
}

// Module 1: pitch radius = teeth. B sits up-right of A (-35deg, center distance 14).
// A's tooth points at B, B's gap points back at A, so they mesh.
const A = { cx: 9.3, cy: 15.5, teeth: 8, pitch: 8 }
const B = { cx: 20.77, cy: 7.47, teeth: 6, pitch: 6 }
const pathA = gearPath(A.cx, A.cy, A.teeth, A.pitch, -35)
const pathB = gearPath(B.cx, B.cy, B.teeth, B.pitch, 55)
</script>

<template>
  <svg
    class="gears"
    viewBox="0 0 28 25"
    :width="size * 1.12"
    :height="size"
    fill-rule="evenodd"
  >
    <path class="gear-a" :fill="colorA" :d="pathA" :style="{ transformOrigin: `${A.cx}px ${A.cy}px` }" />
    <path class="gear-b" :fill="colorB" :d="pathB" :style="{ transformOrigin: `${B.cx}px ${B.cy}px` }" />
  </svg>
</template>

<style scoped>
.gears {
  flex: none;
}
/* A (8 teeth) : B (6 teeth) = 4 : 3, opposite directions */
.gear-a {
  animation: gear-a 4s linear infinite;
}
.gear-b {
  animation: gear-b 4s linear infinite;
}
@keyframes gear-a {
  to {
    transform: rotate(360deg);
  }
}
@keyframes gear-b {
  to {
    transform: rotate(-480deg);
  }
}
</style>
