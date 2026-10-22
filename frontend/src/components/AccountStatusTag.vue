<script setup lang="ts">
import type { AccountStatus } from '@/api/client'

defineProps<{ status: AccountStatus }>()
</script>

<template>
  <span :class="['status', `status--${status.toLowerCase()}`]" data-test="account-status">
    {{ status === 'OPEN' ? 'Open' : 'Closed' }}
  </span>
</template>

<style scoped>
.status {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}

.status::before {
  content: '';
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--p-surface-400);
}

.status--open::before {
  background: var(--p-green-500);
}
</style>
