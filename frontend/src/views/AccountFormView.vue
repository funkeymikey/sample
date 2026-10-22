<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import { computed, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'

import { createAccount, getAccount, updateAccount } from '@/api/client'
import FieldError from '@/components/FieldError.vue'
import { useApiForm } from '@/composables/useApiForm'
import { useRecord } from '@/composables/useRecord'

/** With an `id` this edits that account; without one it opens a new account. */
const props = defineProps<{ id?: string }>()

const router = useRouter()
const toast = useToast()

const isEditing = computed(() => Boolean(props.id))
const { record: existingAccount, notFound, loadError } = useRecord(() => props.id, getAccount)
const { saving, fieldErrors, formError, submit } = useApiForm()

const form = reactive({ account_number: '', holder_name: '', email: '' })

watch(existingAccount, (account) => {
  if (account) {
    Object.assign(form, {
      account_number: account.account_number,
      holder_name: account.holder_name,
      email: account.email,
    })
  }
})

function save() {
  return submit(async () => {
    const account = props.id
      ? await updateAccount(props.id, { holder_name: form.holder_name, email: form.email })
      : await createAccount({
          // Left out when blank, so the API generates one.
          ...(form.account_number.trim() ? { account_number: form.account_number.trim() } : {}),
          holder_name: form.holder_name,
          email: form.email,
        })
    toast.add({ severity: 'success', summary: isEditing.value ? 'Account updated' : 'Account opened', life: 3000 })
    await router.push({ name: 'account', params: { id: account.id } })
  })
}
</script>

<template>
  <main class="page">
    <RouterLink v-if="props.id" :to="{ name: 'account', params: { id: props.id } }" class="back-link">
      <i class="pi pi-arrow-left" aria-hidden="true"></i> Account
    </RouterLink>
    <RouterLink v-else to="/accounts" class="back-link">
      <i class="pi pi-arrow-left" aria-hidden="true"></i> Accounts
    </RouterLink>

    <div class="page-header">
      <div>
        <h1>{{ isEditing ? 'Edit account' : 'Open an account' }}</h1>
        <p v-if="existingAccount" class="subtitle">
          {{ existingAccount.holder_name }} · {{ existingAccount.account_number }}
        </p>
      </div>
    </div>

    <Message v-if="notFound" severity="warn" data-test="not-found">This account doesn't exist.</Message>
    <Message v-else-if="loadError" severity="error" data-test="load-error">{{ loadError }}</Message>
    <Message v-else-if="existingAccount?.status === 'CLOSED'" severity="secondary" data-test="closed-notice">
      This account is closed, so it can't be edited.
    </Message>

    <section v-else-if="!isEditing || existingAccount">
      <form class="form" novalidate data-test="account-form" @submit.prevent="save">
        <Message v-if="formError" severity="error" data-test="form-error">{{ formError }}</Message>

        <div class="field">
          <label for="account-number"> Account number <span v-if="!isEditing" class="muted">(optional)</span> </label>
          <InputText
            id="account-number"
            v-model="form.account_number"
            :disabled="isEditing"
            :invalid="Boolean(fieldErrors.account_number)"
            data-test="account-number-input"
          />
          <small class="hint">
            {{
              isEditing ? "An account number can't change after the account is opened." : 'Leave blank to generate one.'
            }}
          </small>
          <FieldError field="account_number" :errors="fieldErrors.account_number" />
        </div>

        <div class="field">
          <label for="holder-name">Holder name</label>
          <InputText
            id="holder-name"
            v-model="form.holder_name"
            :invalid="Boolean(fieldErrors.holder_name)"
            data-test="holder-name-input"
          />
          <FieldError field="holder_name" :errors="fieldErrors.holder_name" />
        </div>

        <div class="field">
          <label for="email">Email <span class="muted">(optional)</span></label>
          <InputText
            id="email"
            v-model="form.email"
            type="email"
            :invalid="Boolean(fieldErrors.email)"
            data-test="email-input"
          />
          <FieldError field="email" :errors="fieldErrors.email" />
        </div>

        <div class="form-actions">
          <Button type="submit" :label="isEditing ? 'Save changes' : 'Open account'" :loading="saving" />
          <Button
            as="router-link"
            :to="props.id ? { name: 'account', params: { id: props.id } } : '/accounts'"
            label="Cancel"
            severity="secondary"
            text
          />
        </div>
      </form>
    </section>
  </main>
</template>
