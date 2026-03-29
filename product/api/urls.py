from django.urls import path
from .views import (
    DashboardFilterOptionsAPI,
    DashboardSummaryAPI,
    DashboardTrendsAPI,
    DashboardByProvinceAPI,
)

urlpatterns = [
    path("dashboard/filters/", DashboardFilterOptionsAPI.as_view(), name="dashboard-filters"),
    path("dashboard/summary/", DashboardSummaryAPI.as_view(), name="dashboard-summary"),
    path("dashboard/trends/", DashboardTrendsAPI.as_view(), name="dashboard-trends"),
    path("dashboard/by-province/", DashboardByProvinceAPI.as_view(), name="dashboard-by-province"),
]