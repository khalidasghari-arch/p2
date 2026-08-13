from django.urls import path

from .dashboard_views import (
    ganc_dashboard,
)


app_name = "ganc_dashboard"


urlpatterns = [
    path(
        "",
        ganc_dashboard,
        name="dashboard",
    ),
]