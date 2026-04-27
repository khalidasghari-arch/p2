from django.urls import path

from .views import (
    QQMFacilityAnalysisAPI,
    QQMFacilityTrendAPI,
    QQMStructuralDomainAPI,
    QQMStructuralDomainMultiFacilityAPI,
)

urlpatterns = [
    path("analysis/", QQMFacilityAnalysisAPI.as_view(), name="qqm-analysis"),
    path("trend/<int:hfcode>/", QQMFacilityTrendAPI.as_view(), name="qqm-trend"),

    path(
        "structural-domain/<int:hfcode>/",
        QQMStructuralDomainAPI.as_view(),
        name="qqm-structural-domain",
    ),

    path(
        "structural-domain/",
        QQMStructuralDomainMultiFacilityAPI.as_view(),
        name="qqm-structural-domain-multi",
    ),
]