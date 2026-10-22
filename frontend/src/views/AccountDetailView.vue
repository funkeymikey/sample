<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable, { type DataTablePageEvent, type DataTableRowClickEvent } from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import { useToast } from 'primevue/usetoast'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  API_PAGE_SIZE,
  describeError,
  getAccount,
  listAccountTransactions,
  type Transaction,
  type TransactionDirection,
  updateAccount,
} from '@/api/client'
import AccountStatusTag from '@/components/AccountStatusTag.vue'
import InitialsAvatar from '@/components/InitialsAvatar.vue'
import MoneyAmount from '@/components/MoneyAmount.vue'
import { usePagedList } from '@/composables/usePagedList'
import { useRecord } from '@/composables/useRecord'
import { formatDate, signedAmount, toIsoDate } from '@/format'
import { compactQuery, queryChoice, queryDate, queryPage, useQueryUpdater } from '@/routeQuery'

const DIRECTIONS: readonly TransactionDirection[] = ['CREDIT', 'DEBIT']

const props = defineProps<{ id: string }>()

const route = useRoute()
const router = useRouter()
const toast = useToast()

const { record: account, notFound, loadError } = useRecord(() => props.id, getAccount)

// The transaction filters live in the URL (e.g. `?direction=DEBIT&from=2026-09-01&page=2`), so refreshing,
// sharing a link or coming back to the account shows the same transactions.
const direction = computed(() => queryChoice(route.query, 'direction', DIRECTIONS))
const dateFrom = computed(() => queryDate(route.query, 'from'))
const dateTo = computed(() => queryDate(route.query, 'to'))
const pageNumber = computed(() => queryPage(route.query)) // the API's pages start at 1

const confirmingClose = ref(false)
const closing = ref(false)

const directionOptions: { label: string; value: TransactionDirection | null }[] = [
  { label: 'All', value: null },
  { label: 'Credits', value: 'CREDIT' },
  { label: 'Debits', value: 'DEBIT' },
]

// The dates as API strings ("2026-09-01"), which is also how they're compared: reading the URL makes a new Date each time.
const dateFromText = computed(() => (dateFrom.value ? toIsoDate(dateFrom.value) : null))
const dateToText = computed(() => (dateTo.value ? toIsoDate(dateTo.value) : null))

// Puts the transaction filters in the URL, leaving out empty and default values.
const updateQuery = useQueryUpdater(
  () => ({ direction: direction.value, from: dateFromText.value, to: dateToText.value, page: pageNumber.value }),
  (state) => compactQuery({ ...state, page: state.page === 1 ? null : state.page }),
)

const {
  items: transactions,
  total: totalTransactions,
  loading: loadingTransactions,
  loadError: transactionsError,
} = usePagedList(
  () => ({
    accountId: props.id,
    direction: direction.value ?? undefined,
    transaction_date_after: dateFromText.value ?? undefined,
    transaction_date_before: dateToText.value ?? undefined,
    page: pageNumber.value,
  }),
  ({ accountId, ...filters }) => listAccountTransactions(accountId, filters),
  // A saved URL can point past the last page; start over at page 1.
  { onPageGone: () => updateQuery({ page: 1 }) },
)

function changeDirection(value: TransactionDirection | null) {
  updateQuery({ direction: value, page: 1 })
}

/** DatePicker can emit a Date, a list of dates or null; this page only uses single dates. */
function changeDate(boundary: 'from' | 'to', value: unknown) {
  updateQuery({ [boundary]: value instanceof Date ? toIsoDate(value) : null, page: 1 })
}

async function closeAccount() {
  closing.value = true
  try {
    account.value = await updateAccount(props.id, { status: 'CLOSED' })
    toast.add({ severity: 'success', summary: 'Account closed', life: 3000 })
  } catch (error) {
    toast.add({ severity: 'error', summary: "Couldn't close the account", detail: describeError(error).message })
  } finally {
    closing.value = false
    confirmingClose.value = false
  }
}

function changePage(event: DataTablePageEvent) {
  updateQuery({ page: event.page + 1 })
}

function openTransaction(event: DataTableRowClickEvent<Transaction>) {
  router.push({ name: 'transaction', params: { id: event.data.id } })
}
</script>

<template>
  <main class="page">
    <RouterLink to="/accounts" class="back-link"
      ><i class="pi pi-arrow-left" aria-hidden="true"></i> Accounts</RouterLink
    >

    <Message v-if="notFound" severity="warn" data-test="not-found">
      This account doesn't exist. <RouterLink to="/accounts">Back to accounts</RouterLink>
    </Message>
    <Message v-else-if="loadError" severity="error" data-test="load-error">{{ loadError }}</Message>

    <template v-if="account">
      <header class="account-header">
        <div class="identity">
          <InitialsAvatar :name="account.holder_name" size="large" />
          <div>
            <h1 data-test="holder-name">{{ account.holder_name }}</h1>
            <p class="account-meta">
              <span class="mono" data-test="account-number">{{ account.account_number }}</span>
              <span v-if="account.email" class="hide-on-mobile">{{ account.email }}</span>
              <AccountStatusTag :status="account.status" />
            </p>
          </div>
        </div>
        <div class="balance" data-test="balance">
          <span class="eyebrow">Balance</span>
          <MoneyAmount :amount="account.balance" />
        </div>
      </header>

      <div v-if="account.status === 'OPEN'" class="actions account-actions">
        <Button
          as="router-link"
          :to="{ name: 'transaction-new', params: { id: account.id } }"
          label="New transaction"
          icon="pi pi-plus"
          size="small"
          data-test="post-transaction"
        />
        <Button
          as="router-link"
          :to="{ name: 'account-edit', params: { id: account.id } }"
          label="Edit"
          icon="pi pi-pencil"
          severity="secondary"
          text
          size="small"
          data-test="edit-account"
        />
        <Button
          label="Close account"
          icon="pi pi-lock"
          severity="danger"
          text
          size="small"
          data-test="close-account"
          @click="confirmingClose = true"
        />
      </div>
      <Message v-else severity="secondary" class="account-actions" data-test="closed-notice">
        This account is closed. Its history stays here, but it can't be edited or receive new transactions.
      </Message>

      <section class="section">
        <div class="section-header">
          <h2>Transactions</h2>
          <div class="filters">
            <SelectButton
              :model-value="direction"
              :options="directionOptions"
              option-label="label"
              option-value="value"
              :allow-empty="false"
              size="small"
              aria-label="Filter by direction"
              @update:model-value="changeDirection"
            />
            <DatePicker
              :model-value="dateFrom"
              placeholder="From"
              show-button-bar
              show-icon
              icon-display="input"
              size="small"
              class="date-filter"
              aria-label="From date"
              @update:model-value="changeDate('from', $event)"
            />
            <DatePicker
              :model-value="dateTo"
              placeholder="To"
              show-button-bar
              show-icon
              icon-display="input"
              size="small"
              class="date-filter"
              aria-label="To date"
              @update:model-value="changeDate('to', $event)"
            />
          </div>
        </div>

        <Message v-if="transactionsError" severity="error" data-test="transactions-error">
          {{ transactionsError }}
        </Message>

        <DataTable
          :value="transactions"
          data-key="id"
          lazy
          paginator
          :always-show-paginator="false"
          :rows="API_PAGE_SIZE"
          :total-records="totalTransactions"
          :first="(pageNumber - 1) * API_PAGE_SIZE"
          :loading="loadingTransactions"
          class="minimal-table"
          :pt="{ bodyRow: { 'data-test': 'transaction-row' } }"
          @page="changePage"
          @row-click="openTransaction"
        >
          <template #empty><span class="muted" data-test="empty">No transactions yet.</span></template>
          <Column header="Date">
            <template #body="{ data }">
              <span class="muted nowrap">{{ formatDate(data.transaction_date) }}</span>
            </template>
          </Column>
          <Column header="Description">
            <template #body="{ data }">
              <span class="transaction-title">
                <i
                  :class="[
                    'direction-icon',
                    data.direction === 'CREDIT' ? 'pi pi-arrow-down-left' : 'pi pi-arrow-up-right',
                  ]"
                  :title="data.direction === 'CREDIT' ? 'Money in' : 'Money out'"
                ></i>
                <span>
                  {{ data.description || (data.direction === 'CREDIT' ? 'Credit' : 'Debit') }}
                  <RouterLink
                    :to="{ name: 'transaction', params: { id: data.id } }"
                    class="mono muted reference"
                    data-test="transaction-link"
                  >
                    {{ data.reference_id }}
                  </RouterLink>
                </span>
              </span>
            </template>
          </Column>
          <Column header="Amount" header-class="align-right" body-class="align-right">
            <template #body="{ data }">
              <span data-test="transaction-amount">
                <MoneyAmount :amount="signedAmount(data.direction, data.amount)" show-sign />
              </span>
            </template>
          </Column>
        </DataTable>
      </section>

      <Dialog v-model:visible="confirmingClose" modal header="Close this account?" :style="{ width: '26rem' }">
        <p class="muted">Closing is final: the account can't be reopened, edited or receive new transactions.</p>
        <template #footer>
          <Button label="Cancel" severity="secondary" text @click="confirmingClose = false" />
          <Button
            label="Close account"
            severity="danger"
            :loading="closing"
            data-test="confirm-close"
            @click="closeAccount"
          />
        </template>
      </Dialog>
    </template>
  </main>
</template>

<style scoped>
.account-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.5rem 2rem;
}

.identity {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.identity h1 {
  font-size: 2rem;
  line-height: 1.15;
}

.account-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 1rem;
  margin: 0.35rem 0 0;
  color: var(--p-text-muted-color);
}

.balance {
  display: grid;
  justify-items: end;
  gap: 0.2rem;
  font-size: 2.5rem;
  font-weight: 600;
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.account-actions {
  margin-top: 1.5rem;
}

.transaction-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.direction-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 50%;
  background: var(--p-surface-100);
  color: var(--p-surface-500);
  font-size: 0.7rem;
}

.reference {
  margin-left: 0.4rem;
}

.nowrap {
  white-space: nowrap;
}

@media (max-width: 640px) {
  .account-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .balance {
    justify-items: start;
    font-size: 2rem;
  }

  .identity h1 {
    font-size: 1.6rem;
  }
}
</style>
