<script setup lang="ts">
import Toast from 'primevue/toast'
import { onMounted, ref } from 'vue'

import { ApiError, getHealth, type Health } from '@/api/client'

type ApiStatus = Health['status'] | 'checking…' | 'error' | 'unreachable'

const apiStatus = ref<ApiStatus>('checking…')

onMounted(async () => {
  try {
    apiStatus.value = (await getHealth()).status
  } catch (error) {
    // An error in the API's own format means it answered; anything else means it never did.
    apiStatus.value = error instanceof ApiError && error.errorResponse ? 'error' : 'unreachable'
  }
})
</script>

<template>
  <header class="app-header">
    <div class="app-header-inner">
      <RouterLink to="/accounts" class="brand" data-test="home-link">
        <img src="/icons8-money-box-ios-27-filled-32.png" alt="" width="20" height="20" />
        Ledger
      </RouterLink>
      <span class="api-status" :class="`api-status--${apiStatus === 'ok' ? 'ok' : 'problem'}`" title="API status">
        <span class="api-status-dot" aria-hidden="true"></span>
        API <span data-test="api-status">{{ apiStatus }}</span>
      </span>
    </div>
  </header>
  <Toast />
  <RouterView />
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgb(255 255 255 / 0.85);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--p-surface-200);
}

.app-header-inner {
  display: flex;
  align-items: center;
  gap: 1.75rem;
  max-width: var(--app-max-width);
  height: 3.25rem;
  margin: 0 auto;
  padding: 0 1.25rem;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.brand:hover {
  text-decoration: none;
}

.api-status {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-left: auto;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.api-status-dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--p-red-500);
}

.api-status--ok .api-status-dot {
  background: var(--p-green-500);
}

.api-status--problem {
  color: var(--p-red-600);
}
</style>
