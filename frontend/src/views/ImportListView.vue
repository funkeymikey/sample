<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable, { type DataTablePageEvent, type DataTableRowClickEvent } from 'primevue/datatable'
import Message from 'primevue/message'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { API_PAGE_SIZE, type ImportBatch, listImports } from '@/api/client'
import ImportStatusTag from '@/components/ImportStatusTag.vue'
import { usePagedList } from '@/composables/usePagedList'
import { formatDateTime } from '@/format'
import { compactQuery, queryPage, useQueryUpdater } from '@/routeQuery'

const route = useRoute()
const router = useRouter()

const pageNumber = computed(() => queryPage(route.query)) // the API's pages start at 1
const updateQuery = useQueryUpdater(
  () => ({ page: pageNumber.value }),
  (state) => compactQuery({ page: state.page === 1 ? null : state.page }),
)

const {
  items: imports,
  total: totalImports,
  loading,
  loadError,
} = usePagedList(() => ({ page: pageNumber.value }), listImports, {
  // A saved URL can point past the last page; start over at page 1.
  onPageGone: () => updateQuery({ page: 1 }),
})

function changePage(event: DataTablePageEvent) {
  updateQuery({ page: event.page + 1 })
}

function openImport(event: DataTableRowClickEvent<ImportBatch>) {
  router.push({ name: 'import', params: { id: event.data.id } })
}
</script>

<template>
  <main class="page">
    <div class="page-header">
      <div>
        <h1>Imports</h1>
        <p class="subtitle">CSV files of transactions. Each one is posted in full, or not at all.</p>
      </div>
      <Button as="router-link" to="/imports/new" label="Upload CSV" icon="pi pi-upload" data-test="upload-link" />
    </div>

    <Message v-if="loadError" severity="error" data-test="load-error">{{ loadError }}</Message>

    <DataTable
      :value="imports"
      data-key="id"
      lazy
      paginator
      :always-show-paginator="false"
      :rows="API_PAGE_SIZE"
      :total-records="totalImports"
      :first="(pageNumber - 1) * API_PAGE_SIZE"
      :loading="loading"
      class="minimal-table"
      :pt="{ bodyRow: { 'data-test': 'import-row' } }"
      @page="changePage"
      @row-click="openImport"
    >
      <template #empty>
        <span class="muted" data-test="empty">No imports yet. Upload a CSV, or start with the sample file.</span>
      </template>
      <Column header="File">
        <template #body="{ data }">
          <RouterLink :to="{ name: 'import', params: { id: data.id } }" class="file-name" data-test="import-link">
            {{ data.original_filename }}
          </RouterLink>
        </template>
      </Column>
      <Column header="Uploaded" header-class="hide-on-mobile" body-class="hide-on-mobile muted">
        <template #body="{ data }">{{ formatDateTime(data.created_at) }}</template>
      </Column>
      <Column header="Status">
        <template #body="{ data }"><ImportStatusTag :status="data.status" /></template>
      </Column>
      <Column header="Rows" header-class="align-right" body-class="align-right">
        <template #body="{ data }">
          <span class="numeric">{{ data.row_count.toLocaleString() }}</span>
          <span v-if="data.error_count" class="numeric errors">
            · {{ data.error_count.toLocaleString() }} with errors</span
          >
        </template>
      </Column>
    </DataTable>
  </main>
</template>

<style scoped>
.file-name {
  font-weight: 500;
}

.numeric {
  font-variant-numeric: tabular-nums;
}

.errors {
  color: var(--p-red-600);
}
</style>
