<script setup lang="ts">
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
  <h1>Ledger</h1>
  <p>
    API: <strong data-test="api-status">{{ apiStatus }}</strong>
  </p>
  <RouterView />
</template>
