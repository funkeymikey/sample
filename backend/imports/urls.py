from django.urls import path

from imports import views

urlpatterns = [
    path("imports/", views.ImportListView.as_view(), name="import-list"),
    # Before `imports/<pk>/`, which would otherwise match "sample.csv" as an id.
    path("imports/sample.csv", views.SampleFileView.as_view(), name="import-sample"),
    path("imports/<pk>/", views.ImportDetailView.as_view(), name="import-detail"),
    path("imports/<pk>/errors/", views.ImportErrorListView.as_view(), name="import-errors"),
    path("imports/<pk>/errors.csv", views.ImportErrorCsvView.as_view(), name="import-errors-csv"),
    path("imports/<pk>/file/", views.ImportFileView.as_view(), name="import-file"),
]
