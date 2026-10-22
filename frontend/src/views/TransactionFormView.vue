<script setup lang="ts">
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import { useToast } from 'primevue/usetoast'
import { reactive } from 'vue'
import { useRouter } from 'vue-router'

import { getAccount, postTransaction, type TransactionDirection } from '@/api/client'
import FieldError from '@/components/FieldError.vue'
import { useApiForm } from '@/composables/useApiForm'
import { useRecord } from '@/composables/useRecord'
import { toIsoDate, toMoneyString } from '@/format'

const props = defineProps<{ accountId: string }>()

const router = useRouter()
const toast = useToast()

const { record: account, notFound, loadError } = useRecord(() => props.accountId, getAccount)
const { saving, fieldErrors, formError, submit } = useApiForm()

const form = reactive<{
  direction: TransactionDirection
  amount: number | null
  transactionDate: Date | null
  referenceId: string
  description: string
}>({ direction: 'CREDIT', amount: null, transactionDate: new Date(), referenceId: '', description: '' })

const directionOptions: { label: string; value: TransactionDirection }[] = [
  { label: 'Credit (money in)', value: 'CREDIT' },
  { label: 'Debit (money out)', value: 'DEBIT' },
]

function save() {
  return submit(async () => {
    await postTransaction(props.accountId, {
      direction: form.direction,
      // Empty values go to the API as blanks, so it reports them like any other invalid field.
      amount: form.amount === null ? '' : toMoneyString(form.amount),
      transaction_date: form.transactionDate ? toIsoDate(form.transactionDate) : '',
      // Left out when blank, so the API generates one.
      ...(form.referenceId.trim() ? { reference_id: form.referenceId.trim() } : {}),
      description: form.description,
    })
    toast.add({ severity: 'success', summary: 'Transaction posted', life: 3000 })
    await router.push({ name: 'account', params: { id: props.accountId } })
  })
}
</script>

<template>
  <main class="page">
    <RouterLink :to="{ name: 'account', params: { id: props.accountId } }" class="back-link">
      <i class="pi pi-arrow-left" aria-hidden="true"></i> Account
    </RouterLink>

    <div class="page-header">
      <div>
        <h1>Post a transaction</h1>
        <p v-if="account" class="subtitle">To {{ account.holder_name }} · {{ account.account_number }}</p>
      </div>
    </div>

    <Message v-if="notFound" severity="warn" data-test="not-found">This account doesn't exist.</Message>
    <Message v-else-if="loadError" severity="error" data-test="load-error">{{ loadError }}</Message>
    <Message v-else-if="account?.status === 'CLOSED'" severity="secondary" data-test="closed-notice">
      This account is closed, so it can't receive transactions.
    </Message>

    <section v-else-if="account">
      <form class="form" novalidate data-test="transaction-form" @submit.prevent="save">
        <Message v-if="formError" severity="error" data-test="form-error">{{ formError }}</Message>

        <div class="field">
          <label>Direction</label>
          <SelectButton
            v-model="form.direction"
            :options="directionOptions"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            aria-label="Direction"
          />
          <FieldError field="direction" :errors="fieldErrors.direction" />
        </div>

        <div class="field-row">
          <div class="field">
            <label for="amount">Amount</label>
            <InputNumber
              v-model="form.amount"
              input-id="amount"
              mode="currency"
              currency="USD"
              locale="en-US"
              :min="0"
              :invalid="Boolean(fieldErrors.amount)"
              data-test="amount-input"
            />
            <FieldError field="amount" :errors="fieldErrors.amount" />
          </div>

          <div class="field">
            <label for="transaction-date">Date</label>
            <DatePicker
              v-model="form.transactionDate"
              input-id="transaction-date"
              show-icon
              icon-display="input"
              :invalid="Boolean(fieldErrors.transaction_date)"
            />
            <FieldError field="transaction_date" :errors="fieldErrors.transaction_date" />
          </div>
        </div>

        <div class="field">
          <label for="reference-id">Reference <span class="muted">(optional)</span></label>
          <InputText
            id="reference-id"
            v-model="form.referenceId"
            :invalid="Boolean(fieldErrors.reference_id)"
            data-test="reference-id-input"
          />
          <small class="hint">
            Leave blank to generate one. If you give one, it can be used once per account, so re-sending the same
            transaction can't post it twice.
          </small>
          <FieldError field="reference_id" :errors="fieldErrors.reference_id" />
        </div>

        <div class="field">
          <label for="description">Description <span class="muted">(optional)</span></label>
          <InputText id="description" v-model="form.description" data-test="description-input" />
          <FieldError field="description" :errors="fieldErrors.description" />
        </div>

        <div class="form-actions">
          <Button type="submit" label="Post transaction" :loading="saving" />
          <Button
            as="router-link"
            :to="{ name: 'account', params: { id: props.accountId } }"
            label="Cancel"
            severity="secondary"
            text
          />
        </div>
      </form>
    </section>
  </main>
</template>

<style scoped>
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.field-row .p-inputnumber,
.field-row .p-datepicker {
  width: 100%;
}

@media (max-width: 640px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
