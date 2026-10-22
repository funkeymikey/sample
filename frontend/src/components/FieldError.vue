<script setup lang="ts">
defineProps<{ field: string; errors?: string[] }>()
</script>

<template>
  <small v-if="errors?.length" class="field-error" :data-test="`error-${field}`">{{ errors.join(' ') }}</small>
</template>
