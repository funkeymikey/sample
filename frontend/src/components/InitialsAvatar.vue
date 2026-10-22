<script setup lang="ts">
import { computed } from 'vue'

import { initials } from '@/format'

const props = defineProps<{ name: string; size?: 'small' | 'large' }>()

const letters = computed(() => initials(props.name))
</script>

<template>
  <span :class="['avatar', `avatar--${size ?? 'small'}`]" aria-hidden="true">{{ letters }}</span>
</template>

<style scoped>
.avatar {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--p-surface-100);
  color: var(--p-surface-600);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.avatar--small {
  width: 2rem;
  height: 2rem;
  font-size: 0.75rem;
}

.avatar--large {
  width: 3.5rem;
  height: 3.5rem;
  font-size: 1.15rem;
}
</style>
