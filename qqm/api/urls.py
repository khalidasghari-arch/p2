from django.urls import path
from .views import QQMFacilityAnalysisAPI, QQMFacilityTrendAPI

urlpatterns = [
    path("analysis/", QQMFacilityAnalysisAPI.as_view(), name="qqm-analysis"),
    path("trend/<int:hfcode>/", QQMFacilityTrendAPI.as_view(), name="qqm-trend"),
]