from django.urls import path

from ledger import views

urlpatterns = [
    path("accounts/", views.AccountListView.as_view(), name="account-list"),
    path("accounts/<pk>/", views.AccountDetailView.as_view(), name="account-detail"),
    path("accounts/<pk>/transactions/", views.AccountTransactionListView.as_view(), name="account-transactions"),
    path("transactions/<pk>/", views.TransactionDetailView.as_view(), name="transaction-detail"),
]
