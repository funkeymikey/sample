<script setup lang="ts">
import Button from 'primevue/button'
import Message from 'primevue/message'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { sampleFileUrl, uploadImport } from '@/api/client'
import { useApiForm } from '@/composables/useApiForm'

const COLUMNS = [
  { name: 'account_number', note: 'an existing open account' },
  { name: 'direction', note: 'CREDIT (money in) or DEBIT (money out)' },
  { name: 'amount', note: 'positive, at most 2 decimal places, e.g. 125.50' },
  { name: 'transaction_date', note: 'YYYY-MM-DD' },
  { name: 'reference_id', note: 'your ID for the row; each can be used once per account' },
  { name: 'description', note: 'optional' },
]

const router = useRouter()
const { saving, formError, submit } = useApiForm()

const file = ref<File | null>(null)
const dragging = ref(false)

function chooseFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

function dropFile(event: DragEvent) {
  dragging.value = false
  file.value = event.dataTransfer?.files[0] ?? null
}

function upload() {
  const chosenFile = file.value
  if (!chosenFile) {
    return
  }
  return submit(async () => {
    const batch = await uploadImport(chosenFile)
    await router.push({ name: 'import', params: { id: batch.id } })
  })
}
</script>

<template>
  <main class="page">
    <RouterLink to="/imports" class="back-link"><i class="pi pi-arrow-left" aria-hidden="true"></i> Imports</RouterLink>

    <div class="page-header">
      <div>
        <h1>Upload transactions</h1>
        <p class="subtitle">All or nothing: if any row has a problem, nothing is posted, and you'll see what to fix.</p>
      </div>
    </div>

    <div class="layout">
      <form class="form" novalidate @submit.prevent="upload">
        <Message v-if="formError" severity="error" data-test="form-error">{{ formError }}</Message>

        <label
          data-test="drop-zone"
          :class="['drop-zone', { 'drop-zone--active': dragging, 'drop-zone--chosen': file }]"
          @dragover.prevent="dragging = true"
          @dragleave="dragging = false"
          @drop.prevent="dropFile"
        >
          <input type="file" accept=".csv,text/csv" class="file-input" data-test="file-input" @change="chooseFile" />
          <i class="pi pi-upload drop-zone-icon" aria-hidden="true"></i>
          <span v-if="file" data-test="chosen-file">
            <strong>{{ file.name }}</strong>
            <span class="muted"> · {{ (file.size / 1024).toFixed(1) }} KB · click to choose another</span>
          </span>
          <span v-else> <strong>Choose a CSV file</strong> <span class="muted">or drag it here</span> </span>
          <span class="muted hint">UTF-8, up to 5 MB and 10,000 rows</span>
        </label>

        <div class="form-actions">
          <Button
            type="submit"
            label="Upload"
            icon="pi pi-check"
            :disabled="!file"
            :loading="saving"
            data-test="upload-button"
          />
          <Button as="router-link" to="/imports" label="Cancel" severity="secondary" text />
        </div>
      </form>

      <aside class="guide">
        <h2>Columns</h2>
        <dl class="columns">
          <template v-for="column in COLUMNS" :key="column.name">
            <dt class="mono">{{ column.name }}</dt>
            <dd class="muted">{{ column.note }}</dd>
          </template>
        </dl>
        <p class="muted">Other columns are ignored, so a downloaded error file can be fixed and uploaded again.</p>
        <div class="samples">
          <a :href="sampleFileUrl()" download data-test="sample-file">
            <i class="pi pi-download" aria-hidden="true"></i> Download sample file
          </a>
          <a :href="sampleFileUrl({ invalid: true })" download data-test="sample-file-invalid">
            <i class="pi pi-download" aria-hidden="true"></i> Download sample with errors
          </a>
        </div>
      </aside>
    </div>
  </main>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 20rem;
  gap: 3rem;
  align-items: start;
}

.drop-zone {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 0.4rem;
  padding: 2.5rem 1.5rem;
  border: 1.5px dashed var(--p-surface-300);
  border-radius: 0.75rem;
  text-align: center;
  cursor: pointer;
  transition:
    border-color 0.15s,
    background-color 0.15s;
}

.drop-zone:hover,
.drop-zone--active {
  border-color: var(--p-surface-500);
  background: var(--p-surface-50);
}

.drop-zone--chosen {
  border-style: solid;
}

/* Covers the whole drop zone, so clicking anywhere opens the file picker; invisible but still focusable. */
.file-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.drop-zone:focus-within {
  outline: 2px solid var(--p-surface-900);
  outline-offset: 2px;
}

.drop-zone-icon {
  font-size: 1.25rem;
  color: var(--p-text-muted-color);
}

.hint {
  font-size: 0.8rem;
}

.guide h2 {
  margin-bottom: 0.75rem;
  font-size: 1rem;
}

.columns {
  display: grid;
  gap: 0.15rem;
  margin: 0 0 1rem;
}

.columns dd {
  margin: 0 0 0.5rem;
  font-size: 0.85rem;
}

.guide p {
  font-size: 0.85rem;
}

.samples {
  display: grid;
  gap: 0.5rem;
  margin-top: 1.25rem;
  font-size: 0.9rem;
}

@media (max-width: 760px) {
  .layout {
    grid-template-columns: 1fr;
    gap: 2rem;
  }
}
</style>
