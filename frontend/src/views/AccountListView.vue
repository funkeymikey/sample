<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable, {
  type DataTablePageEvent,
  type DataTableRowClickEvent,
  type DataTableSortEvent,
} from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { type Account, API_PAGE_SIZE, type AccountStatus, listAccounts } from '@/api/client'
import AccountStatusTag from '@/components/AccountStatusTag.vue'
import InitialsAvatar from '@/components/InitialsAvatar.vue'
import MoneyAmount from '@/components/MoneyAmount.vue'
import { usePagedList } from '@/composables/usePagedList'
import { compactQuery, queryChoice, queryPage, queryValue, useQueryUpdater } from '@/routeQuery'

const SEARCH_DELAY_MS = 300
const DEFAULT_ORDERING = 'account_number'
const SORTABLE_FIELDS = ['account_number', 'holder_name', 'balance', 'created_at']
const STATUSES: readonly AccountStatus[] = ['OPEN', 'CLOSED']

const route = useRoute()
const router = useRouter()

// The URL is the source of truth for the list's state, so refreshing, sharing a link or going back
// shows the same list. Changing a filter updates the URL, which reloads the list.
const search = computed(() => queryValue(route.query, 'search') ?? '')
const status = computed(() => queryChoice(route.query, 'status', STATUSES))
const ordering = computed(() => {
  const value = queryValue(route.query, 'ordering')
  return value && SORTABLE_FIELDS.includes(value.replace(/^-/, '')) ? value : DEFAULT_ORDERING
})
const pageNumber = computed(() => queryPage(route.query)) // the API's pages start at 1

const searchText = ref(search.value) // what's in the search box; it reaches the URL once the user stops typing

const statusOptions: { label: string; value: AccountStatus | null }[] = [
  { label: 'All', value: null },
  { label: 'Open', value: 'OPEN' },
  { label: 'Closed', value: 'CLOSED' },
]

// DataTable shows the sort as a field plus direction; the API takes one `ordering` value like "-balance".
const sortField = computed(() => ordering.value.replace(/^-/, ''))
const sortOrder = computed(() => (ordering.value.startsWith('-') ? -1 : 1))

// Puts the list's state in the URL, leaving out default values.
const updateQuery = useQueryUpdater(
  () => ({ search: search.value, status: status.value, ordering: ordering.value, page: pageNumber.value }),
  (state) =>
    compactQuery({
      ...state,
      ordering: state.ordering === DEFAULT_ORDERING ? null : state.ordering,
      page: state.page === 1 ? null : state.page,
    }),
)

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(searchText, (text) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (text.trim() !== search.value) {
      updateQuery({ search: text.trim(), page: 1 })
    }
  }, SEARCH_DELAY_MS)
})
onBeforeUnmount(() => clearTimeout(searchTimer))

// Keep the search box in step when the URL changes some other way (e.g. clicking "Accounts").
watch(search, (value) => {
  if (value !== searchText.value.trim()) {
    searchText.value = value
  }
})

const {
  items: accounts,
  total: totalAccounts,
  loading,
  loadError,
} = usePagedList(
  () => ({
    search: search.value || undefined,
    status: status.value ?? undefined,
    ordering: ordering.value,
    page: pageNumber.value,
  }),
  listAccounts,
  // A saved URL can point past the last page once the list has shrunk; start over at page 1.
  { onPageGone: () => updateQuery({ page: 1 }) },
)

function changeStatus(value: AccountStatus | null) {
  updateQuery({ status: value, page: 1 })
}

function changePage(event: DataTablePageEvent) {
  updateQuery({ page: event.page + 1 })
}

function changeSort(event: DataTableSortEvent) {
  const field = typeof event.sortField === 'string' ? event.sortField : null
  updateQuery({ ordering: field ? `${event.sortOrder === -1 ? '-' : ''}${field}` : DEFAULT_ORDERING, page: 1 })
}

function openAccount(event: DataTableRowClickEvent<Account>) {
  router.push({ name: 'account', params: { id: event.data.id } })
}
</script>

<template>
  <main class="page">
    <div class="page-header">
      <div>
        <h1>Accounts</h1>
        <p class="subtitle" data-test="account-count">
          {{ totalAccounts === 1 ? '1 account' : `${totalAccounts} accounts` }}
        </p>
      </div>
      <Button as="router-link" to="/accounts/new" label="New account" icon="pi pi-plus" data-test="open-account" />
    </div>

    <div class="toolbar">
      <IconField class="search-field">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="searchText"
          placeholder="Search by name, account number or email"
          aria-label="Search accounts"
          data-test="account-search"
        />
      </IconField>
      <SelectButton
        :model-value="status"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        size="small"
        aria-label="Filter by status"
        @update:model-value="changeStatus"
      />
    </div>

    <Message v-if="loadError" severity="error" data-test="load-error">{{ loadError }}</Message>

    <DataTable
      :value="accounts"
      data-key="id"
      lazy
      paginator
      :always-show-paginator="false"
      :rows="API_PAGE_SIZE"
      :total-records="totalAccounts"
      :first="(pageNumber - 1) * API_PAGE_SIZE"
      :sort-field="sortField"
      :sort-order="sortOrder"
      :loading="loading"
      class="minimal-table"
      :pt="{ bodyRow: { 'data-test': 'account-row' } }"
      @page="changePage"
      @sort="changeSort"
      @row-click="openAccount"
    >
      <template #empty><span class="muted" data-test="empty">No accounts match.</span></template>
      <Column field="holder_name" header="Holder" sortable>
        <template #body="{ data }">
          <span class="person">
            <InitialsAvatar :name="data.holder_name" />
            <span class="person-name">{{ data.holder_name }}</span>
          </span>
        </template>
      </Column>
      <Column field="account_number" header="Account number" sortable>
        <template #body="{ data }">
          <RouterLink :to="{ name: 'account', params: { id: data.id } }" class="mono muted" data-test="account-number">
            {{ data.account_number }}
          </RouterLink>
        </template>
      </Column>
      <Column field="email" header="Email" header-class="hide-on-mobile" body-class="hide-on-mobile muted" />
      <Column header="Status" header-class="hide-on-mobile" body-class="hide-on-mobile">
        <template #body="{ data }"><AccountStatusTag :status="data.status" /></template>
      </Column>
      <Column field="balance" header="Balance" sortable header-class="align-right" body-class="align-right">
        <template #body="{ data }"><MoneyAmount :amount="data.balance" /></template>
      </Column>
    </DataTable>
  </main>
</template>
