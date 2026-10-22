<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable, { type DataTablePageEvent } from 'primevue/datatable'
import Message from 'primevue/message'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { API_PAGE_SIZE, getImport, importErrorsCsvUrl, importFileUrl, listImportErrors } from '@/api/client'
import ImportStatusTag from '@/components/ImportStatusTag.vue'
import { usePagedList } from '@/composables/usePagedList'
import { useRecord } from '@/composables/useRecord'
import { formatDateTime } from '@/format'
import { compactQuery, queryPage, useQueryUpdater } from '@/routeQuery'

const props = defineProps<{ id: string }>()

const route = useRoute()

const { record: batch, notFound, loadError } = useRecord(() => props.id, getImport)

// The row errors' page lives in the URL, like the other lists.
const pageNumber = computed(() => queryPage(route.query))
const updateQuery = useQueryUpdater(
  () => ({ page: pageNumber.value }),
  (state) => compactQuery({ page: state.page === 1 ? null : state.page }),
)

// Only a failed import has row errors to load.
const failedImportId = computed(() => (batch.value?.status === 'FAILED' ? batch.value.id : null))
const {
  items: rowErrors,
  total: totalRowErrors,
  loading: loadingRowErrors,
  loadError: rowErrorsError,
} = usePagedList(
  () => ({ importId: failedImportId.value, page: pageNumber.value }),
  ({ importId, page }) =>
    importId ? listImportErrors(importId, { page }) : Promise.resolve({ count: 0, results: [] }),
  { onPageGone: () => updateQuery({ page: 1 }) },
)

function changePage(event: DataTablePageEvent) {
  updateQuery({ page: event.page + 1 })
}

/** "amount: Too small." for each field, one per line. */
function describeProblems(errors: Record<string, string[]>): string[] {
  return Object.entries(errors).map(([field, messages]) => `${field}: ${messages.join(' ')}`)
}
</script>

<template>
  <main class="page">
    <RouterLink to="/imports" class="back-link"><i class="pi pi-arrow-left" aria-hidden="true"></i> Imports</RouterLink>

    <Message v-if="notFound" severity="warn" data-test="not-found">This import doesn't exist.</Message>
    <Message v-else-if="loadError" severity="error" data-test="load-error">{{ loadError }}</Message>

    <template v-if="batch">
      <div class="page-header">
        <div>
          <span class="eyebrow">Import</span>
          <h1>{{ batch.original_filename }}</h1>
          <p class="subtitle meta">
            <ImportStatusTag :status="batch.status" />
            <span>Uploaded {{ formatDateTime(batch.created_at) }}</span>
            <a :href="importFileUrl(batch.id)" download class="original-file" data-test="original-file">
              <i class="pi pi-file" aria-hidden="true"></i> Download original file
            </a>
          </p>
        </div>
      </div>

      <div v-if="batch.status === 'COMPLETED'" class="summary summary--completed" data-test="import-summary">
        <i class="pi pi-check-circle" aria-hidden="true"></i>
        <div>
          <strong>All {{ batch.row_count }} rows were posted.</strong>
          <p class="muted">Each transaction now shows on its account.</p>
        </div>
        <Button as="router-link" to="/accounts" label="View accounts" severity="secondary" text size="small" />
      </div>

      <template v-else-if="batch.status === 'FAILED'">
        <div class="summary summary--failed" data-test="import-summary">
          <i class="pi pi-times-circle" aria-hidden="true"></i>
          <div>
            <strong>{{ batch.error_count }} of {{ batch.row_count }} rows have problems, so nothing was posted.</strong>
            <p class="muted">
              Download the rows to fix, correct them in place, and upload the file again. The extra
              <span class="mono">errors</span> column is ignored on upload.
            </p>
          </div>
          <div class="actions">
            <Button
              as="a"
              :href="importErrorsCsvUrl(batch.id)"
              download
              label="Download rows to fix"
              icon="pi pi-download"
              size="small"
              data-test="errors-csv"
            />
            <Button as="router-link" to="/imports/new" label="Upload again" severity="secondary" text size="small" />
          </div>
        </div>

        <section class="section">
          <div class="section-header"><h2>Problems</h2></div>
          <Message v-if="rowErrorsError" severity="error" data-test="row-errors-error">{{ rowErrorsError }}</Message>
          <DataTable
            :value="rowErrors"
            lazy
            paginator
            :always-show-paginator="false"
            :rows="API_PAGE_SIZE"
            :total-records="totalRowErrors"
            :first="(pageNumber - 1) * API_PAGE_SIZE"
            :loading="loadingRowErrors"
            class="minimal-table static-rows"
            :pt="{ bodyRow: { 'data-test': 'row-error' } }"
            @page="changePage"
          >
            <Column header="Line">
              <template #body="{ data }"
                ><span class="mono" data-test="line">{{ data.row_number }}</span></template
              >
            </Column>
            <Column header="Account">
              <template #body="{ data }">
                <span class="mono">{{ data.raw_data.account_number || '—' }}</span>
              </template>
            </Column>
            <Column header="Reference" header-class="hide-on-mobile" body-class="hide-on-mobile">
              <template #body="{ data }">
                <span class="mono muted">{{ data.raw_data.reference_id || '—' }}</span>
              </template>
            </Column>
            <Column header="Problems">
              <template #body="{ data }">
                <ul class="problems" data-test="problems">
                  <li v-for="problem in describeProblems(data.errors)" :key="problem">{{ problem }}</li>
                </ul>
              </template>
            </Column>
          </DataTable>
        </section>
      </template>

      <Message v-else severity="secondary" data-test="processing">This import is still processing.</Message>
    </template>
  </main>
</template>

<style scoped>
.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 1rem;
}

.original-file {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--p-text-color);
}

.summary {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.75rem 1rem;
  padding: 1rem 1.25rem;
  border: 1px solid var(--p-surface-200);
  border-radius: 0.75rem;
}

.summary > div:first-of-type {
  flex: 1;
  min-width: 14rem;
}

.summary p {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
}

.summary > .pi {
  margin-top: 0.15rem;
  font-size: 1.15rem;
}

.summary--completed > .pi {
  color: var(--p-green-600);
}

.summary--failed > .pi {
  color: var(--p-red-600);
}

.problems {
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--p-red-700);
  font-size: 0.875rem;
}

/* Row errors aren't links, so the table shouldn't look clickable. */
.static-rows :deep(.p-datatable-tbody > tr) {
  cursor: default;
}
</style>
