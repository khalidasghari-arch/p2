from django.urls import path

from .dashboard_views import ganc_dashboard
from .women_tracking_views import women_tracking_dashboard


app_name = "ganc_dashboard"


urlpatterns = [

    # ========================================================
    # MAIN GANC / PNC DASHBOARD
    # ========================================================

    path(
        "",
        ganc_dashboard,
        name="dashboard",
    ),

    # ========================================================
    # WOMEN TRACKING
    # ========================================================

    path(
        "women-tracking/",
        women_tracking_dashboard,
        name="women_tracking",
    ),
]