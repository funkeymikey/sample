import '@fontsource-variable/inter'
import 'primeicons/primeicons.css'
import '@/assets/main.css'

import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { createApp } from 'vue'

import App from '@/App.vue'
import router from '@/router'
import { LedgerTheme } from '@/theme'

const app = createApp(App)

app.use(router)
// Light theme only: dark mode would apply under a `.app-dark` class, which nothing sets.
app.use(PrimeVue, { theme: { preset: LedgerTheme, options: { darkModeSelector: '.app-dark' } } })
app.use(ToastService)

app.mount('#app')
