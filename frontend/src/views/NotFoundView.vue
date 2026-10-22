<script setup lang="ts">
import Message from 'primevue/message'
</script>

<template>
  <main class="page">
    <Message severity="warn" data-test="not-found">
      That page doesn't exist. <RouterLink to="/accounts">Back to accounts</RouterLink>
    </Message>
  </main>
</template>
