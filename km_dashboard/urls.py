from django.urls import path
from .views import km_dashboard, districts_api, facilities_api

app_name = "km_dashboard"

urlpatterns = [
    path("", km_dashboard, name="home"),
    path("api/districts/", districts_api, name="districts_api"),
    path("api/facilities/", facilities_api, name="facilities_api"),
]
