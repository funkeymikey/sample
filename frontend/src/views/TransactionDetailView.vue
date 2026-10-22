<script setup lang="ts">
import Message from 'primevue/message'

import { getTransaction } from '@/api/client'
import MoneyAmount from '@/components/MoneyAmount.vue'
import { useRecord } from '@/composables/useRecord'
import { formatDate, formatDateTime, signedAmount } from '@/format'

const props = defineProps<{ id: string }>()

const { record: transaction, notFound, loadError } = useRecord(() => props.id, getTransaction)
</script>

<template>
  <main class="page">
    <RouterLink
      v-if="transaction"
      :to="{ name: 'account', params: { id: transaction.account } }"
      class="back-link"
      data-test="account-link"
    >
      <i class="pi pi-arrow-left" aria-hidden="true"></i> Account
    </RouterLink>
    <RouterLink v-else to="/accounts" class="back-link">
      <i class="pi pi-arrow-left" aria-hidden="true"></i> Accounts
    </RouterLink>

    <Message v-if="notFound" severity="warn" data-test="not-found">This transaction doesn't exist.</Message>
    <Message v-else-if="loadError" severity="error" data-test="load-error">{{ loadError }}</Message>

    <section v-if="transaction" class="transaction">
      <span class="eyebrow">{{ transaction.direction === 'CREDIT' ? 'Money in' : 'Money out' }}</span>
      <div class="amount" data-test="transaction-amount">
        <MoneyAmount :amount="signedAmount(transaction.direction, transaction.amount)" show-sign />
      </div>
      <h1>{{ transaction.description || (transaction.direction === 'CREDIT' ? 'Credit' : 'Debit') }}</h1>

      <dl class="details">
        <dt>Reference</dt>
        <dd class="mono" data-test="reference-id">{{ transaction.reference_id }}</dd>
        <dt>Direction</dt>
        <dd>{{ transaction.direction === 'CREDIT' ? 'Credit' : 'Debit' }}</dd>
        <dt>Date</dt>
        <dd data-test="transaction-date">{{ formatDate(transaction.transaction_date) }}</dd>
        <dt>Recorded</dt>
        <dd>{{ formatDateTime(transaction.created_at) }}</dd>
      </dl>

      <p class="note">
        <i class="pi pi-info-circle" aria-hidden="true"></i>
        Transactions can't be edited or deleted. To correct this one, post a transaction for the same amount in the
        opposite direction.
      </p>
    </section>
  </main>
</template>

<style scoped>
.transaction {
  max-width: 36rem;
}

.amount {
  margin: 0.35rem 0 0.25rem;
  font-size: 3rem;
  font-weight: 600;
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.transaction h1 {
  margin-bottom: 2rem;
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
}

.note {
  display: flex;
  gap: 0.5rem;
  margin-top: 1.5rem;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}

.note .pi {
  margin-top: 0.15rem;
}
</style>
