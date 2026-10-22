<script setup lang="ts">
import type { ImportStatus } from '@/api/client'

defineProps<{ status: ImportStatus }>()

const LABELS: Record<ImportStatus, string> = { PROCESSING: 'Processing', COMPLETED: 'Completed', FAILED: 'Failed' }
</script>

<template>
  <span :class="['status', `status--${status.toLowerCase()}`]" data-test="import-status">{{ LABELS[status] }}</span>
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

.status--completed::before {
  background: var(--p-green-500);
}

.status--failed::before {
  background: var(--p-red-500);
}

.status--failed {
  color: var(--p-red-600);
}
</style>
