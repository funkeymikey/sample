<script setup lang="ts">
import { computed } from 'vue'

import { formatMoney } from '@/format'

/** `showSign` marks money moving in or out: "+$100.00" in green, "-$40.25" in red. */
const props = defineProps<{ amount: string; showSign?: boolean }>()

const sign = computed(() => (props.amount.startsWith('-') ? 'negative' : 'positive'))
</script>

<template>
  <span data-test="money" :data-sign="sign" :class="['money', `money--${sign}`, { 'money--signed': showSign }]">
    {{ formatMoney(amount, { showSign }) }}
  </span>
</template>

<style scoped>
.money {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.money--negative {
  color: var(--p-red-600);
}

.money--signed.money--positive {
  color: var(--p-green-700);
}
</style>
