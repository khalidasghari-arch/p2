from django.urls import path

from . import views

app_name = "facility_snapshot"

urlpatterns = [
    path("", views.facility_list, name="list"),
    path("<int:facility_id>/", views.facility_snapshot, name="detail"),
]
