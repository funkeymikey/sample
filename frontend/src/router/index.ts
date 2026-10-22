import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/accounts' },
  { path: '/accounts', name: 'accounts', component: () => import('@/views/AccountListView.vue') },
  { path: '/accounts/new', name: 'account-new', component: () => import('@/views/AccountFormView.vue') },
  {
    path: '/accounts/:id',
    name: 'account',
    component: () => import('@/views/AccountDetailView.vue'),
    props: true,
  },
  {
    path: '/accounts/:id/edit',
    name: 'account-edit',
    component: () => import('@/views/AccountFormView.vue'),
    props: true,
  },
  {
    path: '/accounts/:id/transactions/new',
    name: 'transaction-new',
    component: () => import('@/views/TransactionFormView.vue'),
    props: (route) => ({ accountId: route.params.id }),
  },
  {
    path: '/transactions/:id',
    name: 'transaction',
    component: () => import('@/views/TransactionDetailView.vue'),
    props: true,
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
