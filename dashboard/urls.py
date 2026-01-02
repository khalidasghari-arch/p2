from django.urls import path
from . import views

urlpatterns = [
    path("hqip/start/", views.hqip_start, name="hqip_start"),
    path("hqip/areas/", views.hqip_area_list, name="hqip_area_list"),
    path("hqip/areas/<int:area_id>/entry/", views.hqip_area_entry, name="hqip_area_entry"),
]
